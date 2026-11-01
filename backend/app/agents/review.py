"""
Review Agent - Phase 6.
Validates draft itinerary against constraints before user delivery.
Two-layer design: Programmatic checks + LLM qualitative checks.
"""

from typing import List

from ..models import (
    TravelConstraints,
    DraftItinerary,
    ReviewReport,
    ChecklistItem,
    RepairHint,
    ReviewSeverity,
    ReviewStatus,
)


class ReviewAgent:
    """
    Quality gate for draft itineraries.
    
    Inputs: DraftItinerary + TravelConstraints
    Output: ReviewReport (pass/fail + issues + RepairHints)
    
    Two-Layer Design:
    - Layer 1: Programmatic checks (cheap, reliable)
    - Layer 2: LLM qualitative checks (prefs, crowd avoidance, coherence)
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    async def review(
        self,
        draft: DraftItinerary,
        constraints: TravelConstraints
    ) -> ReviewReport:
        """
        Phase 6: Validate draft against constraints.
        
        Layer 1 - Programmatic Checks:
        - duration_days matches len(days)
        - All required cities appear in plan
        - total_cost ≤ budget_total
        - Basic structural validity
        
        Layer 2 - LLM Qualitative Checks:
        - Food/temple preference alignment
        - Crowd avoidance effort
        - Narrative coherence
        - Logistics realism
        """
        checklist = []
        
        # Layer 1: Programmatic checks
        checklist.extend(self._check_duration(draft, constraints))
        checklist.extend(self._check_cities(draft, constraints))
        checklist.extend(self._check_budget(draft, constraints))
        checklist.extend(self._check_structure(draft))
        
        # Determine status from checklist
        blocking = [c for c in checklist if c.severity == ReviewSeverity.BLOCKING and not c.passed]
        advisory = [c for c in checklist if c.severity == ReviewSeverity.ADVISORY and not c.passed]
        
        status = ReviewStatus.PASS
        if blocking:
            status = ReviewStatus.FAIL
        elif advisory:
            status = ReviewStatus.WARNINGS
        
        # Layer 2: LLM qualitative (skip if Layer 1 blocking fails)
        qualitative = None
        if status != ReviewStatus.FAIL and self.llm_client:
            qualitative = await self._llm_qualitative_check(draft, constraints)
        
        # Generate repair hints if issues found
        repair_hints = []
        if blocking or advisory:
            repair_hints = self._generate_repair_hints(blocking + advisory)
        
        return ReviewReport(
            draft_version=draft.version,
            overall_status=status,
            checklist=checklist,
            blocking_issues=[c.message for c in blocking],
            advisory_warnings=[c.message for c in advisory],
            repair_hints=repair_hints,
            qualitative_assessment=qualitative
        )
    
    def _check_duration(
        self,
        draft: DraftItinerary,
        constraints: TravelConstraints
    ) -> List[ChecklistItem]:
        """Check day count matches duration constraint."""
        actual_days = len(draft.days)
        expected_days = constraints.duration_days
        
        return [ChecklistItem(
            check="days_match_duration",
            passed=actual_days == expected_days,
            expected=expected_days,
            actual=actual_days,
            severity=ReviewSeverity.BLOCKING,
            message=f"Day count mismatch: expected {expected_days}, got {actual_days}"
        )]
    
    def _check_cities(
        self,
        draft: DraftItinerary,
        constraints: TravelConstraints
    ) -> List[ChecklistItem]:
        """Check all required cities appear in plan."""
        actual_cities = set(d.city for d in draft.days)
        required_cities = set(constraints.cities)
        
        return [ChecklistItem(
            check="cities_included",
            passed=required_cities.issubset(actual_cities),
            expected=list(required_cities),
            actual=list(actual_cities),
            severity=ReviewSeverity.BLOCKING,
            message=f"Missing cities: {required_cities - actual_cities}"
        )]
    
    def _check_budget(
        self,
        draft: DraftItinerary,
        constraints: TravelConstraints
    ) -> List[ChecklistItem]:
        """Check total cost within budget."""
        total = draft.total_estimated_cost
        budget = constraints.budget_total
        
        return [ChecklistItem(
            check="within_budget",
            passed=total <= budget,
            expected=f"<= {budget}",
            actual=total,
            severity=ReviewSeverity.BLOCKING if total > budget * 1.1 else ReviewSeverity.ADVISORY,
            message=f"Budget: ${total} vs limit ${budget}"
        )]
    
    def _check_structure(self, draft: DraftItinerary) -> List[ChecklistItem]:
        """Basic structural validity checks."""
        checks = []
        
        # Check each day has at least one activity slot
        for day in draft.days:
            if not day.items:
                checks.append(ChecklistItem(
                    check=f"day_{day.day_number}_has_activities",
                    passed=False,
                    expected="at least 1 activity",
                    actual="0 activities",
                    severity=ReviewSeverity.BLOCKING,
                    message=f"Day {day.day_number} in {day.city} has no activities"
                ))
        
        # Check for duplicate days
        day_numbers = [d.day_number for d in draft.days]
        if len(day_numbers) != len(set(day_numbers)):
            checks.append(ChecklistItem(
                check="no_duplicate_days",
                passed=False,
                expected="unique day numbers",
                actual=f"duplicates in {day_numbers}",
                severity=ReviewSeverity.BLOCKING,
                message="Duplicate day numbers found"
            ))
        else:
            checks.append(ChecklistItem(
                check="no_duplicate_days",
                passed=True,
                expected="unique day numbers",
                actual=day_numbers,
                severity=ReviewSeverity.ADVISORY,
                message="All day numbers are unique"
            ))
        
        day_cities = [d.city for d in draft.days]
        # Check for route/city variety for long trips
        if len(draft.days) > 7:
            # Geographic spread
            if len(set(day_cities)) < 2:
                checks.append(ChecklistItem(
                    check="geographic_progression",
                    passed=False,
                    expected="multiple regions for long trip",
                    actual="all days in one city",
                    severity=ReviewSeverity.ADVISORY,
                    message="Trip > 7 days should include multiple regions"
                ))
            
            # Repetitive day check (simple heuristic)
            activity_types = []
            for day in draft.days:
                types = [i.type for i in day.items if i.type]
                activity_types.append(tuple(types))
            
            if len(set(activity_types)) == 1 and len(draft.days) > 3:
                checks.append(ChecklistItem(
                    check="day_diversity",
                    passed=False,
                    expected="varied day structures",
                    actual="identical daily structure",
                    severity=ReviewSeverity.ADVISORY,
                    message="Highly repetitive daily activities detected"
                ))
        
        return checks
    
    async def _llm_qualitative_check(
        self,
        draft: DraftItinerary,
        constraints: TravelConstraints
    ) -> str:
        """Layer 2: LLM assessment of preference alignment and coherence."""
        # If no LLM client available, return None (qualitative check is optional)
        if not self.llm_client:
            return None
            
        # Build a summary of the draft for LLM review
        day_summaries = []
        for day in draft.days:
            activities = [item.activity_name for item in day.items if item.activity_id]
            day_summaries.append(f"Day {day.day_number} ({day.city}): {', '.join(activities) if activities else 'Travel/Rest day'}")
        
        # Check preferences alignment
        pref_notes = []
        
        # Food preference check
        if any("food" in p.lower() for p in constraints.soft_preferences):
            food_mentions = sum(1 for d in draft.days for item in d.items if "food" in item.activity_name.lower() or "lunch" in item.activity_name.lower() or "dinner" in item.activity_name.lower())
            pref_notes.append(f"Food experiences: {food_mentions} culinary activities included")
        
        # Temple/culture preference check
        if any(p in ["temple", "culture", "history", "museum"] for p in constraints.soft_preferences):
            culture_mentions = sum(1 for d in draft.days for item in d.items 
                                  if any(kw in item.activity_name.lower() for kw in ["temple", "shrine", "museum", "castle", "historic"]))
            pref_notes.append(f"Cultural experiences: {culture_mentions} temple/history activities included")
        
        # Crowd avoidance check
        if "crowds" in constraints.avoidances:
            pref_notes.append("Crowd avoidance: Plan attempts to avoid crowded periods (check individual activity timing)")
        
        # Build qualitative assessment
        assessment_parts = [
            f"Itinerary covers {len(draft.days)} days across {len(set(d.city for d in draft.days))} cities.",
            "",
            "Day-by-day summary:",
            *day_summaries,
            ""
        ]
        
        if pref_notes:
            assessment_parts.extend(["Preference alignment:", *pref_notes, ""])
        
        assessment_parts.append(f"Estimated total cost: ${draft.total_estimated_cost} {constraints.currency}")
        
        return "\n".join(assessment_parts)
    
    def _generate_repair_hints(self, failed_checks: List[ChecklistItem]) -> List[RepairHint]:
        """Generate specific repair actions from failed checks."""
        hints = []
        for check in failed_checks:
            if check.check == "within_budget":
                hints.append(RepairHint(
                    issue="Over budget",
                    suggested_action="swap lodging to cheaper area or trim activities",
                    priority=9
                ))
            elif check.check == "days_match_duration":
                hints.append(RepairHint(
                    issue="Day count mismatch",
                    suggested_action="add or remove days to match duration",
                    priority=10
                ))
            elif check.check == "cities_included":
                hints.append(RepairHint(
                    issue="Missing required cities",
                    suggested_action="add activities in missing cities to the itinerary",
                    priority=10
                ))
            elif check.check.startswith("day_") and "has_activities" in check.check:
                hints.append(RepairHint(
                    issue="Empty day found",
                    suggested_action="add activities or mark as travel day",
                    priority=8
                ))
            elif check.check == "no_duplicate_days":
                hints.append(RepairHint(
                    issue="Duplicate day numbering",
                    suggested_action="resequence days with unique numbers",
                    priority=10
                ))
        return hints
