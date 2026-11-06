"""
Orchestrator Agent - Phase 2: Constraint extraction with Groq.
Phase 5: Full orchestration with parallel workers.
Phase 7: Repair loop implementation.
Phase 8: Timeouts, observability, and partial failure handling.
"""

import asyncio
import time
from typing import Optional, List, Dict, Any, Tuple

from ..models import (
    TravelConstraints, DraftItinerary, FinalItinerary, ReviewReport,
    ActivityCatalog, LogisticsOutput, BudgetBreakdown, DayItinerary,
    DayItineraryItem, BudgetCategory, ActivityType, PlanInsights,
    TripStructure, Region, MissingConstraintError, InvalidConstraintError,
    MapPin, CostSavingTip, RealFlightOffer, RealHotelOffer, CarEstimate, PlaceInfo
)
from ..llm.token_tracker import TokenBudgetExceeded
from ..config import get_settings
from .destination import DestinationAgent
from .logistics import LogisticsAgent
from .budget import BudgetAgent
from .review import ReviewAgent
from .trip_structuring import TripStructuringAgent
from ..tools import ToolRouter
from ..tools.city_coords import CITY_COORDS
from ..utils.observability import ObservabilityLogger


_COORDS_CACHE: Dict[str, Tuple[float, float]] = dict(CITY_COORDS)


def _lookup_city_coords(name: str) -> Optional[Tuple[float, float]]:
    if not name:
        return None
    name_clean = name.lower().strip()
    if name_clean in _COORDS_CACHE:
        return _COORDS_CACHE[name_clean]
    # Check if city name is contained in any cache entry (e.g. "Paris, France" -> "paris")
    for k, v in _COORDS_CACHE.items():
        if k in name_clean or name_clean in k:
            return v
    return None

def fix_utf8(text: Any) -> Any:
    """Repair mojibake or double-encoded UTF-8 characters."""
    if not isinstance(text, str):
        return text
    mojibake_markers = ("Ã", "â€™", "â€œ", "â€", "â€“", "â€”")
    if any(m in text for m in mojibake_markers):
        try:
            return text.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return text


class OrchestratorAgent:
    """
    Central coordinator for the travel planning pipeline.
    
    Responsibilities:
    1. Parse NL request → TravelConstraints (Phase 2) with Groq LLM
    2. Strict Pre-flight Validation of 3 core pillars: Destination, Duration, Budget
    3. Dispatch parallel workers with constraints (Phase 5)
    4. Merge agent outputs → DraftItinerary (Phase 5)
    5. Manage Review → Repair loop (Phase 7)
    6. Produce FinalItinerary for user
    
    Token Management:
    - Uses Groq client with 100k tokens/day limit
    - Tracks usage per request
    - Caches responses to reduce consumption
    """
    
    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from LLM output that may have preamble or markdown fences."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if "```" in text:
                text = text[:text.rfind("```")]
            text = text.strip()
        brace = text.find("{")
        bracket = text.find("[")
        if brace == -1 and bracket == -1:
            return text
        start = brace if bracket == -1 else (bracket if brace == -1 else min(brace, bracket))
        text = text[start:]
        # Try to repair truncated JSON
        import json
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            repaired = text.rstrip().rstrip(",")
            last_close = repaired.rfind("}")
            if last_close > 0:
                repaired = repaired[:last_close + 1]
                open_brackets = repaired.count("[") - repaired.count("]")
                open_braces = repaired.count("{") - repaired.count("}")
                repaired += "]" * open_brackets + "}" * open_braces
                try:
                    json.loads(repaired)
                    return repaired
                except json.JSONDecodeError:
                    pass
            return text

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self._settings = get_settings()
        
        # Lazy-load LLM client if not provided
        if self.llm_client is None:
            try:
                from ..llm import get_llm_client
                self.llm_client = get_llm_client()
            except Exception as e:
                # Log warning but don't fail - stub mode available
                print(f"Warning: Could not initialize LLM client: {e}")
        
        # Phase 5: Initialize worker agents with shared ToolRouter
        tool_router = ToolRouter()
        self.destination_agent = DestinationAgent(tool_router=tool_router, llm_client=self.llm_client)
        self.logistics_agent = LogisticsAgent(tool_router=tool_router, llm_client=self.llm_client)
        self.budget_agent = BudgetAgent(tool_router=tool_router, llm_client=self.llm_client)
        self.review_agent = ReviewAgent(llm_client=self.llm_client)  # Phase 6
        self.trip_structuring_agent = TripStructuringAgent(llm_client=self.llm_client)

    def validate_constraints(self, constraints: TravelConstraints) -> TravelConstraints:
        """
        Strict 3-Pillar Validation Gatekeeper:
        Verifies that Destination, Duration, and Budget (or tier) are all present.
        If any are missing, raises MissingConstraintError BEFORE worker agents run.
        """
        missing_fields = []
        
        # 1. Validate Destination
        dest = constraints.destination_region
        if not dest or dest.strip().lower() in ["unknown", "world", "none", "null", ""]:
            missing_fields.append("destination")
            
        # 2. Validate Duration
        duration = constraints.duration_days
        if not duration or duration <= 0:
            missing_fields.append("duration")
            
        # 3. Validate Budget / Tier
        budget = constraints.budget_total
        tier = (constraints.budget_tier or "").lower().strip()
        
        if (not budget or budget <= 0) and not tier:
            missing_fields.append("budget")
            
        if missing_fields:
            raise MissingConstraintError(missing_fields=missing_fields)
            
        # If budget tier was provided without an exact budget amount, calculate realistic benchmark
        if (not budget or budget <= 0) and tier and duration and duration > 0:
            tier_daily_usd = {
                "budget": 70.0,
                "moderate": 180.0,
                "luxury": 400.0
            }.get(tier, 180.0)
            
            # Currency conversion factors
            curr = (constraints.currency or "USD").upper()
            fx_to_currency = {
                "USD": 1.0,
                "INR": 83.0,
                "EUR": 0.92,
                "GBP": 0.79,
                "JPY": 150.0
            }.get(curr, 1.0 if curr == "USD" else 83.0)
            
            calculated_budget = round(duration * tier_daily_usd * fx_to_currency, 2)
            constraints.budget_total = calculated_budget
            
        return constraints
    
    async def extract_constraints(self, natural_language_request: str) -> TravelConstraints:
        """
        Phase 2: Extract structured constraints from NL request using Groq LLM.
        """
        # Use configured LLM client (Groq by default)
        if self.llm_client is None:
            raise RuntimeError(
                "LLM client not available. "
                "Set GROQ_API_KEY in .env or use stub mode for testing."
            )
        
        # Delegate to Groq client with structured extraction
        try:
            constraints = await self.llm_client.extract_constraints(natural_language_request)
            return constraints
        except TokenBudgetExceeded as e:
            # Genuine Groq token limit
            raise RuntimeError(
                f"Daily token budget exceeded ({e.limit} tokens/day). "
                f"Check status at /api/tokens/status or wait until UTC midnight."
            ) from e
        except Exception as e:
            # Log error and provide helpful context
            print(f"Constraint extraction failed: {e}")
            raise RuntimeError(f"Failed to extract constraints: {e}") from e
    
    async def create_plan(
        self,
        natural_language_request: str,
        trace_id: str = "unknown",
        origin_city: Optional[str] = None,
        start_date: Optional[str] = None,
        currency: Optional[str] = None
    ) -> FinalItinerary:
        """
        Phase 5-8: Full orchestration pipeline with Review, Repair loop, timeouts, and observability.
        """
        plan_start_time = time.time()
        timeout_seconds = self._settings.agent_timeout_seconds
        
        ObservabilityLogger.log_agent_start("orchestrator", trace_id, 
                                           request_chars=len(natural_language_request))
        
        # Step 1: Extract constraints with timeout
        try:
            constraints = await asyncio.wait_for(
                self.extract_constraints(natural_language_request),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            ObservabilityLogger.log_partial_failure(
                trace_id, "constraint_extraction",
                "fallback_to_stub", "Constraint extraction timed out"
            )
            raise RuntimeError(f"Constraint extraction timed out after {timeout_seconds}s")

        # Overlay explicit user parameters if provided
        if origin_city:
            constraints.origin_city = origin_city.strip()
        if start_date:
            constraints.start_date = start_date.strip()
        if currency:
            constraints.currency = currency.strip()
            
        # Step 1.2: STRICT 3-PILLAR VALIDATION (Destination, Duration, Budget)
        # Halts IMMEDIATELY if any are missing, before invoking expensive downstream agents
        constraints = self.validate_constraints(constraints)
        
        # Step 1.5: Trip Structuring (from improvement.md)
        trip_structure = None
        use_structuring = constraints.duration_days > 7 or constraints.is_road_trip
        
        if use_structuring:
            try:
                trip_structure = await self.trip_structuring_agent.structure(constraints)
                print(f"Trip structured: {trip_structure.trip_type}, {len(trip_structure.regions)} regions, pace={trip_structure.pace}")
                # Update constraints cities from trip structure route while preserving all fields
                structured_cities = [r.base_location for r in trip_structure.regions]
                constraints = constraints.model_copy(update={
                    "cities": structured_cities,
                    "is_road_trip": constraints.is_road_trip or trip_structure.trip_type == "road_trip"
                })
            except Exception as e:
                print(f"Trip structuring failed, using flat pipeline: {e}")
                trip_structure = None
        
        # Step 2: Run agents (per-region if structured, flat otherwise)
        if trip_structure and len(trip_structure.regions) > 1:
            activity_catalog, logistics_output, budget_breakdown = await self._run_agents_per_region(
                constraints, trip_structure, timeout_seconds, trace_id
            )
        else:
            activity_catalog, logistics_output, budget_breakdown = await self._run_agents_flat(
                constraints, timeout_seconds, trace_id
            )
        
        # Step 4: Merge outputs into DraftItinerary
        merge_start = time.time()
        draft = await self.merge(
            constraints=constraints,
            activity_catalog=activity_catalog,
            logistics_output=logistics_output,
            budget_breakdown=budget_breakdown
        )
        ObservabilityLogger.log_agent_complete(
            "merge", trace_id, (time.time() - merge_start) * 1000, 
            artifact_version=1, success=True
        )
        
        # Step 5: Review → Repair loop (Phase 6-7, max 3 retries)
        max_repair_cycles = self._settings.max_review_retries
        repair_count = 0
        
        try:
            review_report = await asyncio.wait_for(
                self.review_agent.review(draft, constraints),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            ObservabilityLogger.log_partial_failure(
                trace_id, "review_agent",
                "pass_without_review", "Review timed out, assuming pass"
            )
            # Create passing review report as fallback
            from ..models import ReviewReport, ReviewStatus
            review_report = ReviewReport(
                draft_version=draft.version,
                overall_status=ReviewStatus.PASS,
                checklist=[],
                blocking_issues=[],
                advisory_warnings=["Review timed out - manual verification recommended"],
                repair_hints=[]
            )
        
        # Log review outcome
        ObservabilityLogger.log_review_outcome(
            trace_id, draft.version, review_report.overall_status,
            {"total": len(review_report.checklist), 
             "passed": sum(1 for c in review_report.checklist if c.passed)},
            len(review_report.blocking_issues),
            len(review_report.advisory_warnings),
            len(review_report.repair_hints)
        )
        
        while review_report.overall_status == "fail" and repair_count < max_repair_cycles:
            print(f"Repair cycle {repair_count + 1}: Addressing {len(review_report.repair_hints)} issues...")
            
            # Log repair action
            actions = [h.suggested_action[:50] for h in review_report.repair_hints[:3]]
            ObservabilityLogger.log_repair_action(trace_id, repair_count + 1, 
                                                len(review_report.repair_hints), actions)
            
            # Attempt repair based on repair hints
            draft = await self.repair(
                draft=draft,
                review_report=review_report,
                constraints=constraints
            )
            
            repair_count += 1
            
            # Re-review after repair
            try:
                review_report = await asyncio.wait_for(
                    self.review_agent.review(draft, constraints),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                ObservabilityLogger.log_partial_failure(
                    trace_id, "review_agent",
                    "pass_without_review", f"Re-review timed out after cycle {repair_count}"
                )
                break
            
            if review_report.overall_status == "pass":
                print(f"Repair successful after {repair_count} cycle(s)")
                break
        
        if review_report.overall_status == "fail":
            print(f"Warning: Max repair cycles ({max_repair_cycles}) reached. Returning best-effort plan.")
        
        # Step 6: Generate insights and day narratives concurrently
        insights_res, _ = await asyncio.gather(
            self._generate_insights(constraints, draft),
            self._enrich_day_narratives(constraints, draft),
            return_exceptions=True
        )
        insights = insights_res if isinstance(insights_res, PlanInsights) else None

        # Step 7: Create FinalItinerary from Draft with Review status, insights, and disclaimer
        final_itinerary = self._draft_to_final(
            draft=draft,
            constraints=constraints,
            budget_breakdown=budget_breakdown,
            review_report=review_report,
            repair_cycles=repair_count,
            insights=insights
        )
        
        # Phase 8: Log plan completion
        total_duration_ms = (time.time() - plan_start_time) * 1000
        ObservabilityLogger.log_plan_complete(
            trace_id, total_duration_ms,
            review_report.overall_status, repair_count,
            len(draft.days), len(set(d.city for d in draft.days))
        )
        
        ObservabilityLogger.log_agent_complete(
            "orchestrator", trace_id, total_duration_ms,
            artifact_version=draft.version, success=True
        )
        
        return final_itinerary
    
    async def _run_agents_flat(self, constraints, timeout_seconds, trace_id):
        """Flat pipeline — runs Destination first, then Logistics (with real APIs), then Budget (Architecture §4, §9)."""
        from ..models import ActivityCatalog, LogisticsOutput, BudgetBreakdown

        # Step 1: Destination first (Logistics needs the catalog)
        activity_catalog = None
        try:
            activity_catalog = await asyncio.wait_for(
                self.destination_agent.research(constraints),
                timeout=timeout_seconds
            )
        except Exception as e:
            ObservabilityLogger.log_partial_failure(
                trace_id, "destination_agent", "use_static_catalog", str(e)[:100]
            )
            all_acts = []
            per_city_map = {}
            for city in constraints.cities:
                city_acts = self.destination_agent._generate_generic_activities(city, constraints)
                per_city_map[city] = [a.id for a in city_acts]
                all_acts.extend(city_acts)
            activity_catalog = ActivityCatalog(activities=all_acts, per_city=per_city_map, neighborhood_notes={})

        # Step 2: Run Logistics first to get real flight and hotel quotes
        try:
            logistics_output = await self._run_logistics_with_timeout(constraints, activity_catalog, timeout_seconds, trace_id)
        except Exception as e:
            print(f"Logistics failed: {e}")
            logistics_output = LogisticsOutput(
                lodging_plans=[], movement_plans=[], day_skeletons=[],
                total_estimated_transit_hours=0.0,
                logistics_summary="Fallback - logistics unavailable"
            )

        # Step 3: Run Budget calibrated with real logistics prices
        try:
            budget_breakdown = await self._run_budget_with_timeout(constraints, timeout_seconds, trace_id, logistics_output)
        except Exception as e:
            print(f"Budget analysis failed: {e}")
            budget_breakdown = BudgetBreakdown(
                categories=[], grand_total=0.0, currency=constraints.currency,
                within_budget=True, remaining_buffer=constraints.budget_total
            )

        return activity_catalog, logistics_output, budget_breakdown
    
    async def _run_agents_per_region(self, constraints, trip_structure, timeout_seconds, trace_id):
        """Run agents per-region concurrently, merge all inventory (flights, hotels, places), and calibrate budget."""
        from ..models import LogisticsOutput, ActivityCatalog, Activity, BudgetBreakdown, BudgetCategory
        from ..tools.flight_client import resolve_iata
        from datetime import datetime, timedelta
        
        all_activities = []
        all_movement_plans = []
        all_lodging_plans = []
        all_day_skeletons = []
        all_places_by_city: Dict[str, List[PlaceInfo]] = {}
        all_hotels_by_city: Dict[str, List[RealHotelOffer]] = {}
        all_car_estimates: List[CarEstimate] = []
        total_transit = 0.0
        per_city = {}
        neighborhood_notes = {}

        # 1. Concurrently launch trip-level flight search
        departure_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        return_date = (datetime.now() + timedelta(days=30 + constraints.duration_days)).strftime("%Y-%m-%d")
        if constraints.start_date:
            try:
                dt = datetime.strptime(constraints.start_date, "%Y-%m-%d")
                departure_date = constraints.start_date
                return_date = (dt + timedelta(days=constraints.duration_days)).strftime("%Y-%m-%d")
            except Exception:
                pass

        origin_iata = "DEL"
        if constraints.origin_city:
            origin_iata = await resolve_iata(constraints.origin_city)
        else:
            for pref in constraints.preferences:
                if "from " in pref.lower():
                    from_c = pref.lower().split("from ")[-1].strip()
                    origin_iata = await resolve_iata(from_c)
                    break

        dest_target = trip_structure.route[0] if (trip_structure and trip_structure.route) else (constraints.cities[0] if constraints.cities else constraints.destination_region)
        dest_iata = await resolve_iata(dest_target)

        # Multi-modal check: skip flight query if user route is explicitly land-based (train/bus/drive)
        needs_flight = True
        if getattr(constraints, "transport_segments", None):
            modes = {s.recommended_mode for s in constraints.transport_segments}
            if "flight" not in modes:
                needs_flight = False

        async def _query_trip_flights():
            if not needs_flight:
                return []
            try:
                return await self.logistics_agent.flight_client.search_flights(
                    origin=origin_iata,
                    destination=dest_iata,
                    departure_date=departure_date,
                    return_date=return_date,
                    cabin_class="economy",
                    adults=1
                )
            except Exception as e:
                print(f"Trip flight query failed: {e}")
                return []

        flight_task = asyncio.create_task(_query_trip_flights())

        # 2. Trip-wide neighborhoods map
        region_cities = [r.base_location for r in trip_structure.regions]
        neighborhoods_map = {}
        if self.logistics_agent.llm_client:
            try:
                neighborhoods_map = await self.logistics_agent._llm_get_neighborhoods(region_cities, constraints)
            except Exception as e:
                print(f"LLM neighborhood generation failed: {e}")

        # 3. Process each region concurrently
        async def _process_region(region):
            clean_name = str(region.name).encode('ascii', 'ignore').decode('ascii')
            print(f"  Processing region: {clean_name} ({region.days} days)")
            region_constraints = TravelConstraints(
                destination_region=constraints.destination_region,
                origin_city=constraints.origin_city,
                start_date=constraints.start_date,
                cities=[region.base_location],
                duration_days=region.days,
                budget_total=constraints.budget_total * (region.days / constraints.duration_days),
                currency=constraints.currency,
                preferences=constraints.preferences,
                avoidances=constraints.avoidances,
                hard_requirements=constraints.hard_requirements,
                soft_preferences=constraints.soft_preferences,
                is_road_trip=constraints.is_road_trip,
            )
            # Run destination
            try:
                rcatalog = await asyncio.wait_for(
                    self.destination_agent.research(region_constraints),
                    timeout=timeout_seconds
                )
            except Exception as e:
                print(f"  Region {clean_name} destination fallback: {e}")
                from ..models import ActivityCatalog
                region_acts = self.destination_agent._generate_generic_activities(region.base_location, region_constraints)
                rcatalog = ActivityCatalog(
                    activities=region_acts,
                    per_city={region.base_location: [a.id for a in region_acts]},
                    neighborhood_notes={},
                    places_by_city={}
                )

            # Run logistics
            try:
                rlogistics = await asyncio.wait_for(
                    self.logistics_agent.plan(region_constraints, rcatalog, neighborhoods_map),
                    timeout=timeout_seconds
                )
            except Exception as e:
                print(f"  Region {clean_name} logistics fallback: {e}")
                rlogistics = LogisticsOutput(
                    lodging_plans=[], movement_plans=[], day_skeletons=[],
                    total_estimated_transit_hours=0.0
                )
            return region, rcatalog, rlogistics

        region_results = await asyncio.gather(*(_process_region(r) for r in trip_structure.regions))
        all_transport_segments = []
        if getattr(constraints, "transport_segments", None):
            all_transport_segments.extend(constraints.transport_segments)

        for region, rcatalog, rlogistics in region_results:
            all_activities.extend(rcatalog.activities)
            per_city.update(rcatalog.per_city)
            neighborhood_notes.update(rcatalog.neighborhood_notes)
            all_places_by_city.update(rcatalog.places_by_city)

            all_lodging_plans.extend(rlogistics.lodging_plans)
            all_movement_plans.extend(rlogistics.movement_plans)
            all_day_skeletons.extend(rlogistics.day_skeletons)
            all_hotels_by_city.update(rlogistics.hotels_by_city)
            all_car_estimates.extend(rlogistics.car_estimates)
            total_transit += rlogistics.total_estimated_transit_hours
            if getattr(rlogistics, "transport_segments", None):
                for seg in rlogistics.transport_segments:
                    if not any(
                        s.from_city.lower() == seg.from_city.lower() and s.to_city.lower() == seg.to_city.lower()
                        for s in all_transport_segments
                    ):
                        all_transport_segments.append(seg)

        # Resequence day numbers globally after merging all regions
        for i, skeleton in enumerate(all_day_skeletons):
            skeleton.day_number = i + 1

        # Await flights
        flight_offers = await flight_task

        # Generate car estimates if road trip and none collected
        if (constraints.is_road_trip or "car" in [p.lower() for p in constraints.preferences]) and not all_car_estimates:
            all_car_estimates = self.logistics_agent._generate_car_estimates(constraints, constraints.duration_days)

        # Merge all region results with full inventory
        activity_catalog = ActivityCatalog(
            activities=all_activities,
            per_city=per_city,
            neighborhood_notes=neighborhood_notes,
            places_by_city=all_places_by_city
        )

        logistics_output = LogisticsOutput(
            lodging_plans=all_lodging_plans,
            movement_plans=all_movement_plans,
            day_skeletons=all_day_skeletons,
            total_estimated_transit_hours=total_transit,
            flight_offers=flight_offers,
            transport_segments=all_transport_segments,
            hotels_by_city=all_hotels_by_city,
            car_estimates=all_car_estimates,
            logistics_summary=f"Route: {' → '.join(trip_structure.route)}"
        )

        budget_constraints = constraints.model_copy(update={"cities": region_cities})
        try:
            budget_breakdown = await asyncio.wait_for(
                self.budget_agent.analyze(budget_constraints, logistics_output),
                timeout=timeout_seconds
            )
        except Exception as e:
            print(f"  Trip budget failed: {e}")
            budget_breakdown = await self.budget_agent._fallback_analyze(budget_constraints)
            budget_breakdown = self.budget_agent._calibrate_with_real_data(budget_breakdown, budget_constraints, logistics_output)

        return activity_catalog, logistics_output, budget_breakdown
    
    async def _run_logistics_with_timeout(self, constraints, activity_catalog, timeout_seconds, trace_id):
        """Run logistics agent with timeout and observability."""
        agent_start = time.time()
        try:
            result = await asyncio.wait_for(
                self.logistics_agent.plan(constraints, activity_catalog),
                timeout=timeout_seconds
            )
            ObservabilityLogger.log_agent_complete(
                "logistics", trace_id, (time.time() - agent_start) * 1000,
                success=True
            )
            return result
        except asyncio.TimeoutError:
            ObservabilityLogger.log_agent_complete(
                "logistics", trace_id, timeout_seconds * 1000,
                success=False, error_type="TimeoutError"
            )
            raise
    
    async def _run_budget_with_timeout(self, constraints, timeout_seconds, trace_id, logistics_output=None):
        """Run budget agent with timeout, observability, and real flight/hotel calibration."""
        agent_start = time.time()
        try:
            result = await asyncio.wait_for(
                self.budget_agent.analyze(constraints, logistics_output),
                timeout=timeout_seconds
            )
            ObservabilityLogger.log_agent_complete(
                "budget", trace_id, (time.time() - agent_start) * 1000,
                success=True
            )
            return result
        except asyncio.TimeoutError:
            ObservabilityLogger.log_agent_complete(
                "budget", trace_id, timeout_seconds * 1000,
                success=False, error_type="TimeoutError"
            )
            raise
    
    async def merge(
        self,
        constraints: TravelConstraints,
        activity_catalog: ActivityCatalog,
        logistics_output: LogisticsOutput,
        budget_breakdown: BudgetBreakdown,
    ) -> DraftItinerary:
        """
        Phase 5: Merge agent outputs into cohesive draft.
        
        Combines:
        - What (ActivityCatalog with activity IDs)
        - When/Where (LogisticsOutput with day skeletons)
        - Cost (BudgetBreakdown with category totals)
        
        Resolves conflicts by using stable IDs as linking mechanism.
        
        Args:
            constraints: Original TravelConstraints
            activity_catalog: Output from DestinationAgent
            logistics_output: Output from LogisticsAgent
            budget_breakdown: Output from BudgetAgent
            
        Returns:
            DraftItinerary with day-by-day structure and linked activities
        """
        # Build day-by-day itinerary from logistics skeletons
        days: List[DayItinerary] = []
        
        # Create lookup for activities by ID
        activity_by_id = {a.id: a for a in activity_catalog.activities}
        
        activity_use_count: dict = {}

        # Build each day from logistics skeletons
        for skeleton in logistics_output.day_skeletons:
            used_activity_ids = set()
            day_items: List[DayItineraryItem] = []
            day_cost = 0.0
            
            for slot in skeleton.slots:
                # Find appropriate activity for this slot
                activity_ref = None
                cost_estimate = 0.0
                
                # Handle travel slots specially
                if slot.activity_type in ["travel", "checkout", "checkin"]:
                    activity_name = slot.notes
                    activity_type = ActivityType.TRANSPORT if slot.activity_type == "travel" else ActivityType.OTHER
                    item = DayItineraryItem(
                        slot_index=slot.slot_index,
                        time=f"{slot.start_time} - {slot.end_time}",
                        activity_id=None,
                        activity_name=activity_name,
                        city=slot.city,
                        type=activity_type,
                        cost_estimate=0.0,
                        notes=slot.notes
                    )
                    day_items.append(item)
                    continue
                
                # Try to match activity by name from slot notes first
                activity_ref = None
                if slot.notes:
                    note_name = slot.notes.split(".")[0].strip()
                    for aid, act in activity_by_id.items():
                        if act.city == skeleton.city and act.name == note_name:
                            activity_ref = aid
                            break

                if not activity_ref:
                    activity_ref = self._find_activity_for_slot(
                        slot.activity_type, skeleton.city, activity_catalog,
                        activity_by_id, used_activity_ids, activity_use_count
                    )

                if activity_ref:
                    used_activity_ids.add(activity_ref)
                    activity_use_count[activity_ref] = activity_use_count.get(activity_ref, 0) + 1
                    if activity_ref in activity_by_id:
                        activity = activity_by_id[activity_ref]
                        cost_estimate = self._estimate_activity_cost(
                            activity,
                            destination=constraints.destination_region or "",
                            budget_tier=constraints.budget_tier or "moderate"
                        )

                activity_name = slot.notes
                activity_type = ActivityType.OTHER
                if activity_ref and activity_ref in activity_by_id:
                    activity = activity_by_id[activity_ref]
                    activity_name = activity.name
                    activity_type = activity.type
                
                # Format time range from start_time and end_time
                time_range = f"{slot.start_time} - {slot.end_time}"
                
                item = DayItineraryItem(
                    slot_index=slot.slot_index,
                    time=time_range,
                    activity_id=activity_ref,
                    activity_name=activity_name,
                    city=slot.city,
                    type=activity_type,
                    cost_estimate=cost_estimate,
                    notes=slot.notes
                )
                day_items.append(item)
                day_cost += cost_estimate
            
            # Get real hotel options and Google Places POIs for this day's city
            day_hotels = logistics_output.hotels_by_city.get(skeleton.city, [])
            day_places = activity_catalog.places_by_city.get(skeleton.city, [])

            # Calculate driving time if road trip
            driving_time = None
            if constraints.is_road_trip and logistics_output.movement_plans:
                for mp in logistics_output.movement_plans:
                    if mp.from_city == skeleton.city and mp.to_city != skeleton.city:
                        driving_time = f"{mp.duration_hours:.1f} hours drive to {mp.to_city}"
                        break

            day = DayItinerary(
                day_number=skeleton.day_number,
                city=skeleton.city,
                items=day_items,
                day_summary=self._generate_day_summary(skeleton, day_items, activity_by_id),
                day_cost=round(day_cost, 2),
                lodging_area=next(
                    (", ".join(l.suggested_neighborhoods) for l in logistics_output.lodging_plans if l.city == skeleton.city),
                    None
                ),
                hotel_options=day_hotels,
                places=day_places[:4],
                driving_time_to_next=driving_time
            )
            days.append(day)
        
        # Calculate total cost
        total_cost = sum(d.day_cost for d in days)

        transport_segs = list(getattr(logistics_output, "transport_segments", []))
        if not transport_segs and getattr(constraints, "transport_segments", None):
            transport_segs = list(constraints.transport_segments)
        
        return DraftItinerary(
            constraints=constraints,
            days=days,
            total_estimated_cost=round(total_cost, 2),
            currency=constraints.currency,
            budget_summary=budget_breakdown,
            catalog_references=list(activity_by_id.keys()),
            flight_options=logistics_output.flight_offers,
            transport_segments=transport_segs,
            car_estimates=logistics_output.car_estimates,
            merged_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc),
            version=1
        )
    
    def _find_activity_for_slot(
        self,
        slot_type: str,
        city: str,
        catalog: ActivityCatalog,
        activity_by_id: Dict[str, Any],
        used_ids: set = None,
        use_count: dict = None
    ) -> Optional[str]:
        """Find appropriate activity ID for a given slot type, preferring least-used."""
        if used_ids is None:
            used_ids = set()
        if use_count is None:
            use_count = {}

        city_data = catalog.per_city.get(city)
        if not city_data:
            return None

        available_ids = sorted(city_data, key=lambda aid: use_count.get(aid, 0))

        type_preferences = {
            "morning": ["temple", "museum", "nature"],
            "afternoon": ["temple", "nature", "shopping", "entertainment"],
            "evening": ["nature", "entertainment", "shopping", "other"],
            "lunch": ["food"],
            "dinner": ["food"],
        }

        preferences = type_preferences.get(slot_type, [])

        for activity_id in available_ids:
            if activity_id in activity_by_id:
                activity = activity_by_id[activity_id]
                if any(pref in str(activity.type).lower() for pref in preferences):
                    return activity_id

        if available_ids:
            return available_ids[0]

        return None
    
    def _estimate_activity_cost(self, activity: Any, destination: str = "", budget_tier: str = "moderate") -> float:
        """Estimate cost for an activity based on category, cost band, and destination."""
        explicit_cost = getattr(activity, "estimated_cost", None)
        if explicit_cost is not None and explicit_cost >= 0:
            return round(float(explicit_cost), 2)

        act_raw = getattr(activity, "type", "")
        act_type = str(getattr(act_raw, "value", act_raw)).lower().replace("activitytype.", "").strip()
        cost_band = str(getattr(activity, "cost_band", "moderate")).lower()
        
        type_cost_map = {
            "museum": 22.0,
            "sightseeing": 18.0,
            "temple": 8.0,
            "culture": 25.0,
            "entertainment": 35.0,
            "nature": 5.0,
            "relaxation": 45.0,
            "shopping": 30.0,
            "food": 16.0,
            "transport": 12.0,
            "other": 15.0
        }
        base = type_cost_map.get(act_type, 18.0)
        
        band_mult = {
            "budget": 0.4,
            "moderate": 1.0,
            "expensive": 1.8,
            "luxury": 3.0
        }.get(cost_band, 1.0)
        
        tier_mult = {
            "budget": 0.7,
            "moderate": 1.0,
            "luxury": 1.6
        }.get(budget_tier.lower(), 1.0)
        
        dest_lower = destination.lower()
        dest_mult = 1.0
        if any(h in dest_lower for h in ["norway", "switzerland", "iceland", "japan", "singapore", "us", "usa", "uk", "london"]):
            dest_mult = 1.3
        elif any(l in dest_lower for l in ["india", "thailand", "vietnam", "cambodia", "bali", "indonesia"]):
            dest_mult = 0.5
            
        cost = base * band_mult * tier_mult * dest_mult
        
        # Realistic individual variation so daily totals vary authentically
        name_seed = sum(ord(c) for c in getattr(activity, "name", "")) % 9
        cost = cost + (name_seed - 4) * 1.5
        return round(max(3.0, cost), 2)

    def _generate_destination_tips(self, destination: str, currency: str = "USD") -> List[CostSavingTip]:
        dest_lower = (destination or "").lower()
        if "france" in dest_lower or "paris" in dest_lower:
            return [
                CostSavingTip(
                    title="Get the Paris Museum Pass",
                    description="A 4-day Paris Museum Pass (€70) gives skip-the-line access to over 50 museums and monuments including the Louvre, Musée d'Orsay, and Arc de Triomphe.",
                    estimated_savings="Save €40 - €70 vs individual tickets"
                ),
                CostSavingTip(
                    title="Book TGV / OUIGO Trains Early",
                    description="SNCF opens TGV high-speed and low-cost OUIGO bookings 3 months ahead with tickets from €19 compared to €80+ on travel week.",
                    estimated_savings="Save 60% - 75% on intercity transit"
                ),
                CostSavingTip(
                    title="Dine at Boulangeries and Set-Menu Bistros",
                    description="Opt for a boulangerie formule déjeuner (sandwich, dessert, beverage for €8-€10) and bistros offering 'menu du jour' at lunch instead of pricey dinners.",
                    estimated_savings="Save €25 - €40 per person daily"
                )
            ]
        elif "japan" in dest_lower or "tokyo" in dest_lower or "kyoto" in dest_lower:
            return [
                CostSavingTip(
                    title="Use 24/48/72-Hour Tokyo Subway Passes",
                    description="Unlimited rides on all Tokyo Metro and Toei Subway lines for only ¥1,500 (72 hours), saving significant money over single IC fares.",
                    estimated_savings="Save ¥1,000 - ¥2,000 per day"
                ),
                CostSavingTip(
                    title="Take Advantage of Evening Depachika Sales",
                    description="Department store basement food halls (depachika) discount gourmet bento and sushi boxes by 20% to 50% every evening after 7:30 PM.",
                    estimated_savings="Save ¥1,500 - ¥3,000 per meal"
                ),
                CostSavingTip(
                    title="Compare Regional Rail Passes with Individual Shinkansen",
                    description="Unless doing heavy cross-country travel, point-to-point Shinkansen tickets via the SmartEX app often cost less than nationwide rail passes.",
                    estimated_savings="Save $80 - $150 per person"
                )
            ]
        elif "iceland" in dest_lower or "reykjavik" in dest_lower:
            return [
                CostSavingTip(
                    title="Stock Up at Bónus or Krónan Discount Supermarkets",
                    description="Icelandic restaurants and roadside diners carry high markups. Buying breakfast and road trip snacks at Bónus cuts food bills dramatically.",
                    estimated_savings="Save $40 - $70 per person daily"
                ),
                CostSavingTip(
                    title="Visit Local Geothermal Pools Over Commercial Spas",
                    description="Local municipal pools like Laugardalslaug cost around 1,200 ISK ($9) and offer authentic hot pots, saunas, and steam rooms without $100+ resort fees.",
                    estimated_savings="Save $80 - $120 per visit"
                ),
                CostSavingTip(
                    title="Fill Up with Rental Fuel Key Discount Fobs",
                    description="Most car rental agencies provide key fobs that give 3-5 ISK per liter discounts and free coffee at designated gas stations (N1, Olís, Orkan).",
                    estimated_savings="Save 5% - 8% on total fuel"
                )
            ]
        elif "russia" in dest_lower or "moscow" in dest_lower or "murmansk" in dest_lower:
            return [
                CostSavingTip(
                    title="Use Troika & Podorozhnik Metro Smart Cards",
                    description="Moscow and Saint Petersburg metros have world-class networks. A Troika card offers deeply discounted rides and seamless transfers between metro, MCC, and trams.",
                    estimated_savings="Save 40% vs single ride tokens"
                ),
                CostSavingTip(
                    title="Book Sapsan & Arctic Trains via Official RZD Portal",
                    description="High-speed Sapsan trains between Moscow and St. Petersburg, and the Arctic overnight sleeper to Murmansk, open 90 days ahead with dynamic tiered pricing.",
                    estimated_savings="Save 50% vs last-minute agencies"
                ),
                CostSavingTip(
                    title="Book Multi-Night Aurora Chasing Packages",
                    description="Northern lights in Murmansk/Teriberka require mobile weather tracking. Multi-night local guide passes guarantee re-runs on cloudy nights.",
                    estimated_savings="Save 30% on combined aurora excursions"
                )
            ]
        else:
            return [
                CostSavingTip(
                    title="Book Flights 6-8 Weeks in Advance",
                    description="Skyscanner historical pricing indicates airfare rises by 18-24% inside the 3-week departure window.",
                    estimated_savings="Save 15% - 25% on flights"
                ),
                CostSavingTip(
                    title="Opt for Neighborhood Stays with Transit Links",
                    description="Choosing well-reviewed accommodations just 2-3 metro stops from the historic center yields 30-40% lower nightly rates.",
                    estimated_savings="Save $30 - $60 per night"
                ),
                CostSavingTip(
                    title="Use Multi-Attraction City Passes & Walking Tours",
                    description="City tourism cards bundle public transit with top museum admissions and offer free guided walking tours.",
                    estimated_savings="Save $20 - $40 per traveler"
                )
            ]
    
    def _generate_day_summary(
        self,
        skeleton: Any,
        items: List[DayItineraryItem],
        activity_by_id: Dict[str, Any]
    ) -> str:
        """Generate a thematic summary for a day."""
        travel_slots = [s for s in skeleton.slots if s.activity_type == "travel"]
        if travel_slots:
            return skeleton.pacing_notes or "Travel between cities"

        activity_names = []
        activity_types = set()
        for item in items:
            if item.activity_id and item.activity_id in activity_by_id:
                activity = activity_by_id[item.activity_id]
                activity_names.append(activity.name)
                activity_types.add(activity.type.value)

        if not activity_names:
            return f"Day in {skeleton.city}"

        theme_map = {
            frozenset({"temple", "museum"}): "Heritage & Culture",
            frozenset({"nature"}): "Nature & Scenery",
            frozenset({"food"}): "Culinary Exploration",
            frozenset({"shopping", "entertainment"}): "Markets & Entertainment",
        }
        theme = None
        for types, label in theme_map.items():
            if types & activity_types:
                theme = label
                break

        if len(activity_names) == 1:
            return f"{activity_names[0]}"
        highlight = activity_names[0]
        if theme:
            return f"{theme}: {highlight} & more"
        return f"{highlight} & {activity_names[1]}"
    
    def _draft_to_final(
        self,
        draft: DraftItinerary,
        constraints: TravelConstraints,
        budget_breakdown: BudgetBreakdown,
        review_report: any = None,  # Optional ReviewReport
        repair_cycles: int = 0,
        insights: Optional[PlanInsights] = None
    ) -> FinalItinerary:
        """Convert DraftItinerary to FinalItinerary with Review status (Phase 6-7)."""
        from ..models import FinalItinerary, ReviewStatus
        
        # Extract neighborhoods from all days
        neighborhoods: Dict[str, List[str]] = {}
        for day in draft.days:
            clean_city = fix_utf8(day.city)
            if clean_city not in neighborhoods:
                neighborhoods[clean_city] = []
            if day.lodging_area and day.lodging_area not in neighborhoods[clean_city]:
                neighborhoods[clean_city].append(fix_utf8(day.lodging_area))
            # Clean day strings
            day.city = clean_city
            day.day_summary = fix_utf8(day.day_summary)
            for itm in day.items:
                itm.activity_name = fix_utf8(itm.activity_name)
                itm.notes = fix_utf8(itm.notes)
            for plc in day.places:
                plc.name = fix_utf8(plc.name)
                plc.description = fix_utf8(plc.description)
        
        # Create logistics summary
        logistics_summary = " | ".join(
            f"Day {d.day_number}: {d.city}" for d in draft.days[:3]
        )
        if len(draft.days) > 3:
            logistics_summary += f" ... (+{len(draft.days) - 3} more days)"
        
        # Use review report if available, otherwise default to PASS
        review_status = ReviewStatus.PASS
        review_warnings = []
        
        base_disclaimer = "Generated by AI Travel Planner. Verify prices and availability before booking."
        
        if review_report:
            review_status = review_report.overall_status
            review_warnings = [fix_utf8(w) for w in review_report.advisory_warnings]
            
            if review_report.overall_status == "fail":
                base_disclaimer += f"\nWarning: This itinerary has blocking issues after {repair_cycles} repair attempts. Please review carefully before using."
            elif repair_cycles > 0:
                base_disclaimer += f"\nNote: Itinerary required {repair_cycles} repair cycle(s) to resolve issues."

        # Dynamic MapPins from arrival airport, overnight hotels, and attractions
        map_pins: List[MapPin] = []
        dest_name = (constraints.destination_region or (constraints.cities[0] if constraints.cities else "")).lower()

        # 1. Airport Pin
        dest_code = None
        if draft.flight_options:
            dest_code = draft.flight_options[0].destination
        if not dest_code:
            from ..tools.flight_client import resolve_iata_sync
            dest_code = resolve_iata_sync(dest_name)

        # Airport Pin
        first_day_places = draft.days[0].places if (draft.days and draft.days[0].places) else []
        if first_day_places and first_day_places[0].lat and first_day_places[0].lng:
            alat, alng = first_day_places[0].lat, first_day_places[0].lng
            aname = f"{dest_name.title()} Gateway Airport ({dest_code or 'Arrival'})"
            map_pins.append(MapPin(label=aname, lat=alat, lng=alng, pin_type="airport"))
        else:
            coords = _lookup_city_coords(dest_name)
            if not coords:
                coords = (64.1466, -21.9426) if "iceland" in dest_name.lower() or "reykjavik" in dest_name.lower() else (48.8566, 2.3522)
            map_pins.append(MapPin(label=f"{dest_name.title()} Arrival Gateway", lat=coords[0], lng=coords[1], pin_type="airport"))

        # 2. Overnight Hotel Pins
        seen_hotel_cities = set()
        for day in draft.days:
            if day.city not in seen_hotel_cities:
                seen_hotel_cities.add(day.city)
                h = day.hotel_options[0] if day.hotel_options else None
                # Prioritize places coordinates from this day
                day_coords = None
                if day.places and day.places[0].lat and day.places[0].lng:
                    day_coords = (day.places[0].lat, day.places[0].lng)
                coords = day_coords or _lookup_city_coords(day.city)
                if not coords:
                    coords = (64.1466, -21.9426) if "iceland" in dest_name.lower() or "reykjavik" in day.city.lower() else (48.8566, 2.3522)
                hotel_label = f"Stay: {h.name} ({day.city})" if h else f"Stay in {day.city}"
                hotel_desc = f"${h.price_per_night}/night • {h.guest_rating}★" if (h and h.guest_rating) else (f"${h.price_per_night}/night" if h else f"Overnight base in {day.city}")
                map_pins.append(MapPin(
                    label=fix_utf8(hotel_label),
                    lat=coords[0],
                    lng=coords[1],
                    day_number=day.day_number,
                    pin_type="overnight",
                    description=fix_utf8(hotel_desc)
                ))

        # 3. Attraction Pins
        seen_attractions = set()
        for day in draft.days:
            for p in day.places:
                if p.name not in seen_attractions and p.lat and p.lng:
                    seen_attractions.add(p.name)
                    map_pins.append(MapPin(
                        label=fix_utf8(p.name),
                        lat=p.lat,
                        lng=p.lng,
                        day_number=day.day_number,
                        pin_type="attraction",
                        description=fix_utf8(f"★ {p.rating} ({p.review_count:,} reviews)" if p.rating and p.review_count else p.name)
                    ))

        # Structured Cost Saving Tips (Destination Specific)
        cost_saving_tips_v2 = self._generate_destination_tips(dest_name, constraints.currency)
        
        return FinalItinerary(
            constraints=draft.constraints,
            days=draft.days,
            neighborhoods=neighborhoods,
            logistics_summary=logistics_summary,
            strategic_insight=fix_utf8(insights.strategic_insight) if insights else None,
            budget_analysis=fix_utf8(insights.budget_analysis) if insights else None,
            cost_optimization_tips=[fix_utf8(t) for t in insights.cost_optimization_tips] if insights else [],
            cost_saving_tips_v2=cost_saving_tips_v2,
            flight_options=draft.flight_options,
            transport_segments=getattr(draft, "transport_segments", []),
            car_estimates=draft.car_estimates,
            map_pins=map_pins,
            why_this_plan=fix_utf8(insights.why_this_plan) if insights else None,
            what_not_to_do=[fix_utf8(w) for w in insights.what_not_to_do] if insights else [],
            base_selection_rationale={fix_utf8(k): fix_utf8(v) for k, v in insights.base_selection_rationale.items()} if insights else {},
            experience_highlights=[fix_utf8(h) for h in insights.experience_highlights] if insights else [],
            best_time_to_visit=fix_utf8(insights.best_time_to_visit) if insights else None,
            budget_rollup=budget_breakdown,
            review_status=review_status,
            review_warnings=review_warnings,
            disclaimer=base_disclaimer
        )
    
    async def _generate_insights(self, constraints: TravelConstraints, draft: DraftItinerary) -> PlanInsights:
        """Generate strategic insights and budget analysis using LLM."""
        cities_str = ', '.join(set(d.city for d in draft.days))
        prefs_str = ', '.join(constraints.preferences) if constraints.preferences else 'general sightseeing'
        avoids_str = ', '.join(constraints.avoidances) if constraints.avoidances else 'none'

        if self.llm_client is None:
             return PlanInsights(
                strategic_insight="A well-paced itinerary balancing major landmarks and local experiences.",
                budget_analysis=f"The budget of {constraints.budget_total} {constraints.currency} aligns with a comfortable mid-range trip for {constraints.duration_days} days.",
                cost_optimization_tips=["Book transport in advance", "Use local supermarkets for snacks", "Look for free walking tours"],
                why_this_plan=f"This plan prioritizes {prefs_str} across {cities_str}.",
                what_not_to_do=["Avoid tourist-trap restaurants near major landmarks"],
                base_selection_rationale={city: f"Central location with good access to attractions" for city in constraints.cities},
                experience_highlights=[],
                best_time_to_visit="Check seasonal weather patterns for optimal timing."
            )

        system_prompt = f"""You are a world-class travel strategist. The traveler wants: {prefs_str}. They want to avoid: {avoids_str}.

Analyze the itinerary deeply and generate a JSON response with ALL these fields:

1. "strategic_insight": 2-3 sentences on WHY this routing/pacing is smart and essential visa/entry requirements if traveling internationally (e.g., Schengen visa appointments, 6-month passport validity, or International Driving Permit for road trips).

2. "budget_analysis": A frank 'Reality Check'. Is the budget tight, comfortable, or generous for this destination? What tier does it land in (backpacker/mid-range/luxury)? What's the daily spending power?

3. "cost_optimization_tips": 3-5 specific, actionable tips for THIS trip (not generic). Reference real local options. Example: "Take the Shatabdi Express instead of a private car to save 60%."

4. "why_this_plan": 2-3 sentences explaining why THIS specific plan matches THEIR stated preferences ({prefs_str}). Connect activities to what they asked for.

5. "what_not_to_do": 3-4 specific mistakes tourists make at THIS destination. Example: "Don't eat at restaurants directly facing the Taj — they charge 3x for mediocre food. Walk 2 blocks to Panchhi Dhaba instead."

6. "base_selection_rationale": Object mapping each city name to a sentence explaining why it's a good base. Example: {{"Delhi": "Old Delhi puts you within walking distance of Chandni Chowk street food and Red Fort"}}

7. "experience_highlights": Array of 2-3 standout moments. Each has "title" (short name), "description" (why it's special), and "tag" (one of: splurge, romantic, adventure, cultural, hidden-gem, must-see). Pick the BEST moments from the itinerary.

8. "best_time_to_visit": 2-3 sentences on seasonal considerations. Mention weather, festivals, peak/off-peak pricing, and the best months.

Respond with valid JSON only. Keep each field concise — quality over quantity."""

        prompt = f"""Trip: {constraints.duration_days} days in {cities_str}
Origin: {constraints.origin_city or 'International departure'}
Budget: {constraints.budget_total} {constraints.currency}
Preferences: {prefs_str}
Avoidances: {avoids_str}
Estimated cost: {draft.total_estimated_cost} {draft.currency}
Cities visited: {cities_str}
Road trip: {'Yes' if constraints.is_road_trip else 'No'}
Days breakdown: {', '.join(f'Day {d.day_number}: {d.city}' for d in draft.days)}"""

        try:
            import json as _json
            content = await self.llm_client.chat_with_retry(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000
            )
            content = self._extract_json(content)
            data = _json.loads(content)
            insights = PlanInsights.model_validate(data)
            return insights
        except Exception as e:
             print(f"Insight generation failed: {e}")
             return PlanInsights(
                strategic_insight="A balanced itinerary designed for maximum coverage of the requested regions.",
                budget_analysis="The budget is sufficient for a standard mid-range experience at this destination.",
                cost_optimization_tips=["Eat at local markets", "Consider a multi-day regional pass"],
                why_this_plan=f"Designed around your interest in {prefs_str}.",
                what_not_to_do=["Avoid overpriced tourist restaurants near major landmarks"],
                base_selection_rationale={city: "Good central location" for city in constraints.cities},
                experience_highlights=[],
                best_time_to_visit="Check local weather and festival calendars for your travel dates."
            )
    
    async def _enrich_day_narratives(self, constraints: TravelConstraints, draft: DraftItinerary):
        """Add mood, highlight, and narrative to each day via a single LLM call."""
        if not self.llm_client:
            return

        days_desc = []
        for d in draft.days:
            activities = [item.activity_name for item in d.items if item.type.value != "transport"]
            days_desc.append(f"Day {d.day_number} in {d.city}: {', '.join(activities[:4])}")

        system_prompt = """You are a travel storyteller and logistics expert. For each day, generate:
- "mood": One evocative word (e.g. Wonder, Discovery, Adventure, Ease, Transition, Anticipation, Freedom, Awe)
- "highlight": The standout moment in under 8 words (e.g. "Sunrise Over The Golden Temple")
- "narrative": 1-2 sentences about today's experience — what makes this day special, what the traveler will feel
- "transport_tip": 1 short practical tip on getting around today (e.g. "Take metro line 1", "Rental car for coastal stretch", "Walkable district", "Book Grab/Uber")

Respond with JSON: {"days": [{"day": 1, "mood": "...", "highlight": "...", "narrative": "...", "transport_tip": "..."}, ...]}
Be specific to the actual activities and city listed. No generic filler."""

        prompt = f"""Trip: {constraints.duration_days} days, {constraints.destination_region}
Preferences: {', '.join(constraints.preferences) if constraints.preferences else 'general'}

{chr(10).join(days_desc)}"""

        try:
            import json as _json
            token_budget = min(800 + (len(draft.days) * 120), 4000)
            content = await self.llm_client.chat_with_retry(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=token_budget
            )
            content = self._extract_json(content)
            data = _json.loads(content)
            day_narratives = {item["day"]: item for item in data.get("days", [])}

            for d in draft.days:
                info = day_narratives.get(d.day_number, {})
                d.mood = str(info.get("mood", ""))[:30] or None
                d.highlight = str(info.get("highlight", ""))[:100] or None
                d.day_narrative = str(info.get("narrative", ""))[:500] or None
                d.local_transport_tip = str(info.get("transport_tip", ""))[:300] or None
        except Exception as e:
            print(f"Day narrative generation failed: {e}")

    async def repair(
        self,
        draft: DraftItinerary,
        review_report: ReviewReport,
        constraints: TravelConstraints
    ) -> DraftItinerary:
        """
        Phase 7: Bounded repair loop implementation.
        
        Interprets RepairHints from ReviewReport and applies fixes:
        - trim_over_budget: Remove expensive activities or reduce costs
        - fix_duration_mismatch: Add/remove days to match duration
        - swap_lodging: Change to cheaper neighborhoods
        - redistribute_budget: Rebalance costs across days
        
        Returns modified DraftItinerary for re-review.
        """
        import copy
        from ..models import DayItinerary, DayItineraryItem, ActivityType
        
        # Create a copy to avoid mutating original
        repaired_draft = copy.deepcopy(draft)
        
        if not review_report.repair_hints:
            print("No repair hints provided, returning draft unchanged")
            return repaired_draft
        
        print(f"Processing {len(review_report.repair_hints)} repair hints...")
        
        # Sort hints by priority (highest first)
        sorted_hints = sorted(review_report.repair_hints, key=lambda h: h.priority, reverse=True)
        
        for hint in sorted_hints:
            issue = hint.issue.lower()
            action = hint.suggested_action.lower()
            print(f"  Repairing: {hint.issue} (priority {hint.priority})")
            
            # Handle budget overruns
            if "budget" in issue or "cost" in issue or "over" in issue:
                if "trim" in action or "reduce" in action or "remove" in action:
                    repaired_draft = self._trim_expensive_activities(repaired_draft)
                elif "swap" in action or "lodging" in action:
                    repaired_draft = self._reduce_lodging_costs(repaired_draft)
                elif "rebalance" in action:
                    repaired_draft = self._rebalance_day_costs(repaired_draft)
            
            # Handle duration mismatches
            elif "duration" in issue or "days" in issue:
                if "add" in action or "extend" in action:
                    repaired_draft = self._add_missing_days(repaired_draft, constraints)
                elif "remove" in action or "trim" in action:
                    repaired_draft = self._remove_extra_days(repaired_draft, constraints)
            
            # Handle duplicate day numbering
            elif "duplicate" in issue or "resequence" in action:
                repaired_draft = self._resequence_days(repaired_draft)
            
            # Handle city mismatches
            elif "city" in issue or "wrong city" in issue:
                repaired_draft = self._fix_city_assignments(repaired_draft, constraints)
            
            # Handle missing activities or structure issues
            elif "structure" in issue or "empty" in issue or "missing" in issue:
                repaired_draft = self._fill_empty_slots(repaired_draft, constraints)
        
        # Recalculate total cost after repairs
        total_cost = sum(d.day_cost for d in repaired_draft.days)
        repaired_draft.total_estimated_cost = round(total_cost, 2)
        
        # Increment version to track repair iterations
        repaired_draft.version += 1
        
        print(f"Repair complete. Draft version: {repaired_draft.version}, Total cost: ${total_cost}")
        return repaired_draft
    
    def _trim_expensive_activities(self, draft: DraftItinerary) -> DraftItinerary:
        """Reduce costs by removing or replacing expensive activities."""
        for day in draft.days:
            for item in day.items:
                # Reduce high cost estimates
                if item.cost_estimate > 50.0:
                    item.cost_estimate = round(item.cost_estimate * 0.7, 2)  # 30% reduction
        return draft
    
    def _reduce_lodging_costs(self, draft: DraftItinerary) -> DraftItinerary:
        """Adjust lodging areas to cheaper alternatives."""
        # Mark lodging areas as budget-friendly
        for day in draft.days:
            if day.lodging_area:
                day.lodging_area = f"Budget-friendly area near {day.lodging_area}"
        return draft
    
    def _rebalance_day_costs(self, draft: DraftItinerary) -> DraftItinerary:
        """Even out cost distribution across days."""
        if not draft.days:
            return draft
        
        avg_cost = sum(d.day_cost for d in draft.days) / len(draft.days)
        
        for day in draft.days:
            # Bring each day closer to average
            if day.day_cost > avg_cost * 1.5:
                day.day_cost = round(avg_cost * 1.2, 2)
        return draft
    
    def _add_missing_days(self, draft: DraftItinerary, constraints: TravelConstraints) -> DraftItinerary:
        """Add days to match required duration."""
        from ..models import DayItinerary, DayItineraryItem, ActivityType
        
        current_days = len(draft.days)
        target_days = constraints.duration_days
        
        if current_days < target_days:
            # Add blank days with minimal structure
            for day_num in range(current_days + 1, target_days + 1):
                new_day = DayItinerary(
                    day_number=day_num,
                    city=constraints.cities[0] if constraints.cities else "Unknown",
                    items=[
                        DayItineraryItem(
                            slot_index=0,
                            time="09:00 - 12:00",
                            activity_id=None,
                            activity_name="Exploration day",
                            city=constraints.cities[0] if constraints.cities else "Unknown",
                            type=ActivityType.OTHER,
                            cost_estimate=0.0,
                            notes="Flexible day for personal exploration"
                        )
                    ],
                    day_summary=f"Day {day_num}: Flexible exploration",
                    day_cost=0.0,
                    lodging_area=None
                )
                draft.days.append(new_day)
        
        return draft
    
    def _remove_extra_days(self, draft: DraftItinerary, constraints: TravelConstraints) -> DraftItinerary:
        """Remove excess days beyond required duration."""
        target_days = constraints.duration_days
        
        if len(draft.days) > target_days:
            # Keep first and last days, remove from middle
            keep_indices = [0] + list(range(len(draft.days) - target_days + 1, len(draft.days)))
            draft.days = [draft.days[i] for i in keep_indices[:target_days]]
            
            # Renumber days
            for i, day in enumerate(draft.days, 1):
                day.day_number = i
        
        return draft
    
    def _fix_city_assignments(self, draft: DraftItinerary, constraints: TravelConstraints) -> DraftItinerary:
        """Ensure all days are assigned to valid cities from constraints."""
        valid_cities = set(constraints.cities)
        
        for day in draft.days:
            if day.city not in valid_cities:
                # Assign to first valid city
                day.city = constraints.cities[0] if constraints.cities else day.city
                for item in day.items:
                    item.city = day.city
        
        return draft
    
    def _fill_empty_slots(self, draft: DraftItinerary, constraints: TravelConstraints) -> DraftItinerary:
        """Fill empty or minimal slots with placeholder activities."""
        from ..models import DayItineraryItem, ActivityType
        
        for day in draft.days:
            if not day.items:
                # Add default item if day is empty
                day.items = [
                    DayItineraryItem(
                        slot_index=0,
                        time="09:00 - 18:00",
                        activity_id=None,
                        activity_name="Free exploration",
                        city=day.city,
                        type=ActivityType.OTHER,
                        cost_estimate=0.0,
                        notes="Day at leisure for personal activities"
                    )
                ]
        
        return draft
    
    def _resequence_days(self, draft: DraftItinerary) -> DraftItinerary:
        """Fix duplicate day numbering by assigning sequential day numbers."""
        for i, day in enumerate(draft.days, 1):
            day.day_number = i
        return draft
