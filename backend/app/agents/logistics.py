"""
Logistics Agent - Phase 4b.
Handles practical side of moving and staying.
Uses LLM for neighborhood suggestions and route planning.
"""

import asyncio
import json
import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from ..models import (
    TravelConstraints,
    LogisticsOutput,
    LodgingPlan,
    MovementPlan,
    DaySkeleton,
    DaySlot,
    ActivityType,
    CostBand,
    RealFlightOffer,
    RealHotelOffer,
    CarEstimate,
    TransportSegment,
)
from ..tools.flight_client import get_flight_client, resolve_iata
from ..tools.hotel_client import get_hotel_client
from ..utils.currency import to_usd
from ..llm.llm_utils import validate_llm_json, validate_item_fields

logger = logging.getLogger(__name__)


class LogisticsAgent:
    """
    Plans lodging, transport, and day structures.
    Integrates real Skyscanner flight queries, Booking.com hotel data, and car estimates.
    """

    def __init__(self, tool_router=None, llm_client=None, flight_client=None, hotel_client=None):
        self.tool_router = tool_router
        self.llm_client = llm_client
        self.flight_client = flight_client or get_flight_client()
        self.hotel_client = hotel_client or get_hotel_client()

    @staticmethod
    def _extract_json_content(text: str) -> str:
        """Extract JSON from LLM output that may have preamble or markdown fences."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if "```" in text:
                text = text[:text.rfind("```")]
            text = text.strip()
        brace = text.find("{")
        if brace > 0:
            text = text[brace:]
        return text

    async def plan(self, constraints: TravelConstraints, activity_catalog: Optional[any] = None,
                   neighborhoods_map: Optional[Dict[str, List[str]]] = None) -> LogisticsOutput:
        """Generate logistics plan from constraints with real flight and hotel data."""
        cities = constraints.cities
        duration = constraints.duration_days

        # 1. Allocate nights and lodging skeletons
        night_allocation = self._allocate_nights(cities, duration)
        lodging_plans = await self._create_lodging_plans(cities, night_allocation, constraints, activity_catalog, neighborhoods_map)
        movement_plans = await self._create_movement_plans(cities, constraints)
        day_skeletons = self._build_day_skeletons(night_allocation, lodging_plans, movement_plans, constraints, activity_catalog)
        total_transit_hours = sum(m.duration_hours for m in movement_plans)

        route_desc = None
        if constraints.is_road_trip:
            route_desc = await self._generate_route_description(constraints)

        # 2. Query Real Flights via Skyscanner / RapidAPI
        departure_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        return_date = (datetime.now() + timedelta(days=30 + duration)).strftime("%Y-%m-%d")
        if constraints.start_date:
            try:
                dt = datetime.strptime(constraints.start_date, "%Y-%m-%d")
                departure_date = constraints.start_date
                return_date = (dt + timedelta(days=duration)).strftime("%Y-%m-%d")
            except Exception:
                pass

        # Resolve Origin Airport
        origin_iata = "DEL"  # Sensible default global hub
        if constraints.origin_city:
            origin_iata = await resolve_iata(constraints.origin_city)
        else:
            for pref in constraints.preferences:
                if "from " in pref.lower():
                    from_city = pref.lower().split("from ")[-1].strip()
                    origin_iata = await resolve_iata(from_city)
                    break

        dest_target = cities[0] if cities else (constraints.destination_region or "Iceland")
        dest_iata = await resolve_iata(dest_target)

        flight_offers: List[RealFlightOffer] = []
        try:
            flight_offers = await self.flight_client.search_flights(
                origin=origin_iata,
                destination=dest_iata,
                departure_date=departure_date,
                return_date=return_date,
                cabin_class="economy",
                adults=1
            )
        except Exception as e:
            print(f"Logistics flight query failed: {e}")

        # 3. Query Real Hotels via Booking.com RapidAPI (calibrated to budget tier using canonical FX, AG-003)
        per_night_budget = (constraints.budget_total * 0.40 / max(1, duration)) if constraints.budget_total > 0 else 150.0
        per_night_usd = to_usd(per_night_budget, constraints.currency)

        budget_tier = "moderate"
        if per_night_usd > 300 or any(p in [pref.lower() for pref in constraints.preferences] for p in ["luxury", "5-star", "splurge", "lavish", "premium"]):
            budget_tier = "luxury"
        elif per_night_usd < 75 or any(p in [pref.lower() for pref in constraints.preferences] for p in ["budget", "backpack", "hostel", "cheap", "affordable"]):
            budget_tier = "budget"

        hotels_by_city: Dict[str, List[RealHotelOffer]] = {}
        for city in cities:
            try:
                dest = await self.hotel_client.search_destination(city)
                city_nights = night_allocation.get(city, max(1, duration // len(cities)))
                hotels = await self.hotel_client.search_hotels(
                    dest_id=dest["dest_id"],
                    city_name=city,
                    arrival_date=departure_date,
                    departure_date=return_date,
                    adults=1,
                    budget_tier=budget_tier,
                    num_nights=city_nights
                )
                hotels_by_city[city] = hotels
            except Exception as e:
                print(f"Logistics hotel query failed for {city}: {e}")
                hotels_by_city[city] = []

        # 4. Generate Car Rental Estimates if road trip
        car_estimates: List[CarEstimate] = []
        if constraints.is_road_trip or "car" in [p.lower() for p in constraints.preferences]:
            car_estimates = self._generate_car_estimates(constraints, duration)

        # 5. Assemble multi-modal transport segments (Getting There + Inter-City)
        transport_segments: List[TransportSegment] = []
        if constraints.transport_segments:
            transport_segments.extend(constraints.transport_segments)
        else:
            orig_name = constraints.origin_city or "Origin"
            dest_first = cities[0] if cities else (constraints.destination_region or "Destination")
            arrival_mode = "flight"
            if constraints.is_road_trip:
                arrival_mode = "drive"
            elif any("train" in p.lower() for p in constraints.preferences):
                arrival_mode = "train"

            booking_url = f"https://www.skyscanner.com/transport/flights/{origin_iata.lower()}/{dest_iata.lower()}" if arrival_mode == "flight" else f"https://www.thetrainline.com/book/results?origin={orig_name}&destination={dest_first}"
            transport_segments.append(TransportSegment(
                from_city=orig_name,
                to_city=dest_first,
                recommended_mode=arrival_mode,
                reason=f"Arrival transport to {dest_first}",
                estimated_duration_hours=round(flight_offers[0].duration_minutes / 60, 1) if (flight_offers and arrival_mode == "flight") else 2.5,
                estimated_cost_usd=flight_offers[0].price if (flight_offers and arrival_mode == "flight") else 65.0,
                operator_name=flight_offers[0].airline if (flight_offers and arrival_mode == "flight") else ("Regional Rail / Transit" if arrival_mode == "train" else "Rental Vehicle"),
                line_or_flight_number=flight_offers[0].flight_number if (flight_offers and arrival_mode == "flight") else None,
                booking_url=booking_url
            ))

        existing_pairs = {(ts.from_city.lower(), ts.to_city.lower()) for ts in transport_segments}
        for mp in movement_plans:
            pair = (mp.from_city.lower(), mp.to_city.lower())
            if pair not in existing_pairs:
                existing_pairs.add(pair)
                mode_str = mp.mode if mp.mode in ["flight", "train", "bus", "drive", "ferry"] else ("drive" if constraints.is_road_trip else "train")
                op_name = "Intercity Rail" if mode_str == "train" else ("FlixBus / Coach" if mode_str == "bus" else ("Rental Car" if mode_str == "drive" else "Regional Transit"))
                notes_lower = mp.booking_notes.lower()
                if "shinkansen" in notes_lower:
                    op_name = "Shinkansen High-Speed Rail"
                elif "tgv" in notes_lower:
                    op_name = "SNCF TGV InOui"
                elif "railway" in notes_lower or "irctc" in notes_lower:
                    op_name = "Indian Railways"
                elif "sbb" in notes_lower:
                    op_name = "SBB Swiss Federal Railways"

                b_url = f"https://www.thetrainline.com/book/results?origin={mp.from_city}&destination={mp.to_city}" if mode_str == "train" else (f"https://www.google.com/maps/dir/?api=1&origin={mp.from_city}&destination={mp.to_city}" if mode_str == "drive" else "https://global.flixbus.com/")
                transport_segments.append(TransportSegment(
                    from_city=mp.from_city,
                    to_city=mp.to_city,
                    recommended_mode=mode_str,
                    reason=mp.booking_notes or f"Transit from {mp.from_city} to {mp.to_city}",
                    estimated_duration_hours=mp.duration_hours,
                    estimated_cost_usd=round(mp.duration_hours * 25.0, 2),
                    operator_name=op_name,
                    booking_url=b_url
                ))

        return LogisticsOutput(
            lodging_plans=lodging_plans,
            movement_plans=movement_plans,
            day_skeletons=day_skeletons,
            total_estimated_transit_hours=total_transit_hours,
            route_description=route_desc,
            flight_offers=flight_offers,
            transport_segments=transport_segments,
            hotels_by_city=hotels_by_city,
            car_estimates=car_estimates,
            logistics_summary=self._generate_summary(movement_plans)
        )

    def _generate_car_estimates(self, constraints: TravelConstraints, duration: int) -> List[CarEstimate]:
        """Generate realistic car hire options calibrated by destination."""
        region = (constraints.destination_region or "").lower()
        
        if "iceland" in region:
            rate_economy = 55.0
            rate_suv = 85.0
            rate_camper = 140.0
            name_economy = "Toyota Yaris (Gravel Protected)"
            name_suv = "Dacia Duster 4x4 (F-Road Approved)"
            name_camper = "VW Transporter 4x4 Campervan"
        elif "japan" in region:
            rate_economy = 48.0
            rate_suv = 75.0
            rate_camper = 120.0
            name_economy = "Toyota Aqua Hybrid"
            name_suv = "Subaru Forester AWD"
            name_camper = "Toyota HiAce Camper"
        else:
            rate_economy = 42.0
            rate_suv = 70.0
            rate_camper = 110.0
            name_economy = "Volkswagen Polo"
            name_suv = "Nissan Qashqai"
            name_camper = "Ford Transit Custom"
            
        return [
            CarEstimate(
                vehicle_name=name_economy,
                category="Economy",
                price_per_day=rate_economy,
                total_price=round(rate_economy * duration, 2),
                currency="USD",
                seats=4,
                transmission="Automatic",
                is_estimate=True,
                deeplink="https://www.skyscanner.net/carhire"
            ),
            CarEstimate(
                vehicle_name=name_suv,
                category="SUV 4x4",
                price_per_day=rate_suv,
                total_price=round(rate_suv * duration, 2),
                currency="USD",
                seats=5,
                transmission="Automatic",
                is_estimate=True,
                deeplink="https://www.skyscanner.net/carhire"
            ),
            CarEstimate(
                vehicle_name=name_camper,
                category="Campervan",
                price_per_day=rate_camper,
                total_price=round(rate_camper * duration, 2),
                currency="USD",
                seats=4,
                transmission="Manual",
                is_estimate=True,
                deeplink="https://www.skyscanner.net/carhire"
            )
        ]

    def _allocate_nights(self, cities: List[str], duration_days: int) -> Dict[str, int]:
        """Distribute nights across cities."""
        if not cities:
            return {}
        base_nights = duration_days // len(cities)
        remainder = duration_days % len(cities)
        allocation = {}
        for i, city in enumerate(cities):
            allocation[city] = base_nights + (1 if i < remainder else 0)
        return allocation

    async def _create_lodging_plans(self, cities: List[str], night_allocation: Dict[str, int],
                                     constraints: TravelConstraints, activity_catalog: Optional[any],
                                     neighborhoods_map: Optional[Dict[str, List[str]]] = None) -> List[LodgingPlan]:
        """Create lodging plans, using LLM for neighborhood suggestions."""
        plans = []

        if neighborhoods_map is None and self.llm_client:
            try:
                neighborhoods_map = await self._llm_get_neighborhoods(cities, constraints)
            except Exception as e:
                print(f"LLM neighborhood generation failed: {e}")
        neighborhoods_map = neighborhoods_map or {}

        for city in cities:
            nights = night_allocation.get(city, 1)
            neighborhoods = neighborhoods_map.get(city, [f"Central {city}"])

            plan = LodgingPlan(
                city=city,
                nights=nights,
                suggested_neighborhoods=neighborhoods[:3],
                neighborhood_rationale=f"Selected based on proximity to activities in {city}",
                estimated_cost_per_night=CostBand.MODERATE
            )
            plans.append(plan)

        return plans

    async def _llm_get_neighborhoods(self, cities: List[str], constraints: TravelConstraints) -> Dict[str, List[str]]:
        """Use LLM to get best neighborhoods for each city."""
        system_prompt = """You are a travel accommodation expert. For each city, suggest the 3 best neighborhoods to stay in for a tourist.

Respond with valid JSON:
{
  "neighborhoods": {
    "CityName": ["Neighborhood1", "Neighborhood2", "Neighborhood3"]
  }
}

Rules:
- Use REAL neighborhood/district names
- Pick areas that are safe, well-connected, and close to attractions
- Consider the traveler's budget and preferences"""

        user_prompt = f"""Suggest 3 best neighborhoods to stay in for each city:
Cities: {', '.join(cities)}
Preferences: {', '.join(constraints.preferences) if constraints.preferences else 'general sightseeing'}
Budget: {constraints.budget_total} {constraints.currency} for {constraints.duration_days} days"""

        content = await self.llm_client.chat_with_retry(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1200
        )

        content = self._extract_json_content(content)
        data = json.loads(content)
        validate_llm_json(data, required_keys=["neighborhoods"], caller_name="LogisticsAgent._llm_get_neighborhoods")
        return data.get("neighborhoods", {}) if isinstance(data, dict) else {}

    async def _create_movement_plans(self, cities: List[str], constraints: TravelConstraints) -> List[MovementPlan]:
        """Create inter-city movement plans."""
        if len(cities) < 2:
            return []

        if self.llm_client:
            try:
                return await self._llm_generate_movements(cities, constraints)
            except Exception as e:
                print(f"LLM movement planning failed: {e}")

        movements = []
        trace_id = getattr(constraints, 'trace_id', None)

        for i in range(len(cities) - 1):
            from_city = cities[i]
            to_city = cities[i + 1]

            if self.tool_router:
                try:
                    geo_result = await self.tool_router.geo_estimate(
                        from_location=from_city, to_location=to_city, trace_id=trace_id
                    )
                    movement = MovementPlan(
                        from_city=from_city, to_city=to_city,
                        mode=geo_result.get("mode", "transit"),
                        duration_hours=geo_result.get("duration_minutes", 120) / 60,
                        cost_band=CostBand.MODERATE,
                        booking_notes=geo_result.get("notes", "")
                    )
                    movements.append(movement)
                except Exception:
                    movements.append(self._create_fallback_movement(from_city, to_city))
            else:
                movements.append(self._create_fallback_movement(from_city, to_city))

        return movements

    async def _llm_generate_movements(self, cities: List[str], constraints: TravelConstraints) -> List[MovementPlan]:
        """Use LLM to plan inter-city transport with real options."""
        pairs = [f"{cities[i]} to {cities[i+1]}" for i in range(len(cities) - 1)]

        system_prompt = """You are a travel logistics expert. For each city pair, suggest the best transport option.

Respond with valid JSON:
{
  "movements": [
    {
      "from_city": "City A",
      "to_city": "City B",
      "mode": "train|bus|flight|drive|ferry",
      "duration_hours": number,
      "booking_notes": "Specific transport name or tip (e.g., 'Shinkansen Nozomi, book at JR station')"
    }
  ]
}

Rules:
- Use real transport options (train names, airline routes, highway names)
- Duration should be realistic
- Consider budget when suggesting options"""

        user_prompt = f"""Plan transport for these segments:
{chr(10).join(f'- {p}' for p in pairs)}
Trip type: {"road trip (driving)" if constraints.is_road_trip else "multi-city"}
Budget: {constraints.budget_total} {constraints.currency}"""

        content = await self.llm_client.chat_with_retry(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1500
        )

        content = self._extract_json_content(content)
        data = json.loads(content)
        validate_llm_json(data, required_keys=["movements"], caller_name="LogisticsAgent._llm_generate_movements")
        movements = []
        for m in (data.get("movements", []) if isinstance(data, dict) else []):
            if not validate_item_fields(m, ["from_city", "to_city"], caller_name="LogisticsAgent.movement"):
                continue
            movements.append(MovementPlan(
                from_city=m["from_city"],
                to_city=m["to_city"],
                mode=m.get("mode", "transit"),
                duration_hours=float(m.get("duration_hours", 2.0)),
                cost_band=CostBand.MODERATE,
                booking_notes=m.get("booking_notes", "")
            ))
        return movements

    def _create_fallback_movement(self, from_city: str, to_city: str) -> MovementPlan:
        return MovementPlan(
            from_city=from_city, to_city=to_city,
            mode="transit", duration_hours=2.0, cost_band=CostBand.MODERATE,
            booking_notes="Check local transit options"
        )

    def _build_day_skeletons(self, night_allocation: Dict[str, int], lodging_plans: List[LodgingPlan],
                              movement_plans: List[MovementPlan], constraints: TravelConstraints,
                              activity_catalog: Optional[any] = None) -> List[DaySkeleton]:
        """Create day-by-day structure with travel time buffers."""
        skeletons = []
        cities = constraints.cities
        if not cities:
            return skeletons

        current_day = 1
        current_city_idx = 0
        city_day_counter: Dict[str, int] = {}

        while current_day <= constraints.duration_days and current_city_idx < len(cities):
            city = cities[current_city_idx]
            nights_in_city = night_allocation.get(city, 1)

            is_travel_day = False
            travel_buffer_minutes = 0

            if current_city_idx < len(cities) - 1:
                days_remaining = sum(night_allocation.get(cities[i], 1) for i in range(current_city_idx, len(cities)))
                if current_day == constraints.duration_days - days_remaining + nights_in_city:
                    is_travel_day = True
                    if current_city_idx < len(movement_plans):
                        travel_buffer_minutes = int(movement_plans[current_city_idx].duration_hours * 60) + 60

            travel_hours = travel_buffer_minutes / 60
            if is_travel_day:
                next_city = cities[current_city_idx + 1] if current_city_idx + 1 < len(cities) else "next"
                slots = [
                    DaySlot(slot_index=0, start_time="09:00", end_time="10:00",
                            activity_type="checkout", city=city,
                            notes=f"Check out and travel to {next_city}"),
                    DaySlot(slot_index=1, start_time="10:00", end_time=f"{10 + int(travel_hours):02d}:00",
                            activity_type="travel", city=city, notes="Inter-city travel"),
                    DaySlot(slot_index=2, start_time=f"{10 + int(travel_hours):02d}:00",
                            end_time=f"{11 + int(travel_hours):02d}:00",
                            activity_type="checkin", city=cities[current_city_idx + 1],
                            notes=f"Arrive and check in to {cities[current_city_idx + 1]}")
                ]
            else:
                day_idx = city_day_counter.get(city, 0)
                slots = self._generate_day_slots(city, constraints, activity_catalog, day_in_city=day_idx)
                city_day_counter[city] = day_idx + 1

            skeleton = DaySkeleton(
                day_number=current_day, city=city, slots=slots,
                total_travel_time_hours=travel_hours,
                pacing_notes=f"Day in {city}" if not is_travel_day else f"Travel day: {city} -> {cities[current_city_idx + 1] if current_city_idx + 1 < len(cities) else 'next'}"
            )
            skeletons.append(skeleton)

            if is_travel_day or (not is_travel_day and current_day >= sum(night_allocation.get(cities[i], 1) for i in range(current_city_idx + 1))):
                current_city_idx += 1

            current_day += 1

        return skeletons

    def _generate_day_slots(self, city: str, constraints: TravelConstraints,
                             activity_catalog: Optional[any] = None,
                             day_in_city: int = 0) -> List[DaySlot]:
        """Generate day slots with rich activity descriptions, rotating across days."""
        city_activities = []
        if activity_catalog and hasattr(activity_catalog, 'activities'):
            city_activities = [a for a in activity_catalog.activities if a.city == city]

        avoids = [a.lower() for a in constraints.avoidances] if constraints.avoidances else []
        crowd_avoid = any("crowd" in a for a in avoids)

        non_food = [a for a in city_activities if a.type.value != "food"]
        food_acts = [a for a in city_activities if a.type.value == "food"]

        n = len(non_food)
        if n > 0:
            offset = (day_in_city * 3) % n
            available = non_food[offset:] + non_food[:offset]
        else:
            available = []

        def _activity_note(act):
            desc = getattr(act, 'description', None) or getattr(act, 'rationale', None) or ""
            timing = getattr(act, 'best_time', None)
            parts = [f"{act.name}.", desc]
            if timing and crowd_avoid:
                parts.append(timing)
            return " ".join(p for p in parts if p)

        nf = len(food_acts)
        lunch_idx = (day_in_city * 2) % max(1, nf)
        dinner_idx = (day_in_city * 2 + 1) % max(1, nf)

        morning_note = _activity_note(available[0]) if len(available) > 0 else f"Explore {city}'s landmarks."
        lunch_note = _activity_note(food_acts[lunch_idx]) if nf > 0 else f"Lunch at a local restaurant in {city}."
        afternoon_note = _activity_note(available[1]) if len(available) > 1 else f"Explore more of {city}."
        evening_note = _activity_note(available[2]) if len(available) > 2 else f"Evening stroll in {city}."
        dinner_note = _activity_note(food_acts[dinner_idx]) if nf > 1 else lunch_note

        return [
            DaySlot(slot_index=0, start_time="09:00", end_time="12:00",
                    activity_type="morning", city=city, notes=morning_note),
            DaySlot(slot_index=1, start_time="12:00", end_time="13:30",
                    activity_type="lunch", city=city, notes=lunch_note),
            DaySlot(slot_index=2, start_time="14:00", end_time="17:00",
                    activity_type="afternoon", city=city, notes=afternoon_note),
            DaySlot(slot_index=3, start_time="17:30", end_time="19:00",
                    activity_type="evening", city=city, notes=evening_note),
            DaySlot(slot_index=4, start_time="19:30", end_time="21:00",
                    activity_type="dinner", city=city, notes=dinner_note)
        ]

    async def _generate_route_description(self, constraints: TravelConstraints) -> str:
        """Use LLM to generate route description for road trips."""
        if self.llm_client:
            try:
                content = await self.llm_client.chat_with_retry(
                    messages=[
                        {"role": "system", "content": "Write a one-paragraph route overview for a road trip. Be specific about roads, regions, and key stops. Under 150 words."},
                        {"role": "user", "content": f"Road trip through {constraints.destination_region}, {constraints.duration_days} days, cities: {', '.join(constraints.cities)}"}
                    ],
                    max_tokens=300
                )
                return content.strip()
            except Exception:
                pass
        return f"A {constraints.duration_days}-day road trip through {constraints.destination_region}."

    def _generate_summary(self, movement_plans: List[MovementPlan]) -> str:
        if not movement_plans:
            return "Single city stay - no inter-city travel"
        parts = [f"{m.from_city} → {m.to_city} ({m.mode}, {m.duration_hours}h)" for m in movement_plans]
        return " | ".join(parts)
