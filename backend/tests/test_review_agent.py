"""
Unit tests for ReviewAgent (AG-078).
Tests programmatic validation (Layer 1), qualitative LLM review (Layer 2),
blocking vs advisory issue classification, and repair hint generation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.schemas import (
    TravelConstraints,
    DraftItinerary,
    DayItinerary,
    DayItineraryItem,
    ActivityType,
    BudgetBreakdown,
    BudgetCategory,
    ReviewStatus,
    ReviewSeverity,
)
from app.agents.review import ReviewAgent


def _make_dummy_breakdown(total: float = 100.0, currency: str = "EUR") -> BudgetBreakdown:
    """Helper to build a valid BudgetBreakdown satisfying Pydantic schema."""
    return BudgetBreakdown(
        categories=[BudgetCategory(category="stay", estimated_total=total, currency=currency)],
        grand_total=total,
        currency=currency,
        within_budget=True,
        remaining_buffer=0.0
    )


def _create_sample_draft(constraints: TravelConstraints, days_count: int = 3, cities: list = None, total_cost: float = 1000.0) -> DraftItinerary:
    """Helper to build a valid draft itinerary for testing."""
    if cities is None:
        cities = ["Paris"]

    days = []
    cost_per_day = total_cost / max(days_count, 1)
    for idx in range(1, days_count + 1):
        city = cities[(idx - 1) % len(cities)]
        item1_cost = cost_per_day * 0.4
        item2_cost = cost_per_day * 0.6
        days.append(
            DayItinerary(
                day_number=idx,
                city=city,
                items=[
                    DayItineraryItem(
                        slot_index=0,
                        time="09:00 - 12:00",
                        activity_id=f"act-{city.lower()}-walk-{idx}",
                        activity_name=f"{city} Historic Center Walk",
                        city=city,
                        type=ActivityType.CULTURE,
                        cost_estimate=item1_cost,
                        notes="Morning walk"
                    ),
                    DayItineraryItem(
                        slot_index=1,
                        time="14:00 - 17:00",
                        activity_id=f"act-{city.lower()}-mus-{idx}",
                        activity_name=f"{city} Art Museum",
                        city=city,
                        type=ActivityType.MUSEUM,
                        cost_estimate=item2_cost,
                        notes="Afternoon cultural visit"
                    )
                ],
                day_summary=f"Exploring {city}",
                day_cost=cost_per_day
            )
        )

    return DraftItinerary(
        constraints=constraints,
        days=days,
        total_estimated_cost=total_cost,
        currency=constraints.currency,
        budget_summary=_make_dummy_breakdown(total_cost, constraints.currency),
        version=1
    )


@pytest.mark.asyncio
async def test_review_agent_passes_calibrated_plan():
    """Verify ReviewAgent returns PASS when draft matches constraints perfectly."""
    constraints = TravelConstraints(
        origin="LHR",
        destination_region="France",
        duration_days=3,
        cities=["Paris"],
        budget_total=1200.0,
        currency="EUR"
    )
    draft = _create_sample_draft(constraints, days_count=3, cities=["Paris"], total_cost=1000.0)

    agent = ReviewAgent()
    report = await agent.review(draft, constraints)

    assert report.overall_status == ReviewStatus.PASS
    assert len(report.blocking_issues) == 0
    assert len(report.advisory_warnings) == 0


@pytest.mark.asyncio
async def test_review_agent_blocking_duration_mismatch():
    """Verify ReviewAgent fails with BLOCKING issue when duration does not match."""
    constraints = TravelConstraints(
        origin="LHR",
        destination_region="France",
        duration_days=5,
        cities=["Paris"],
        budget_total=2000.0,
        currency="EUR"
    )
    # Draft only has 3 days instead of 5
    draft = _create_sample_draft(constraints, days_count=3, cities=["Paris"], total_cost=1500.0)

    agent = ReviewAgent()
    report = await agent.review(draft, constraints)

    assert report.overall_status == ReviewStatus.FAIL
    assert any("Day count mismatch" in msg for msg in report.blocking_issues)
    assert len(report.repair_hints) > 0


@pytest.mark.asyncio
async def test_review_agent_blocking_missing_cities():
    """Verify ReviewAgent fails when a required city is missing from the itinerary."""
    constraints = TravelConstraints(
        origin="LHR",
        destination_region="France",
        duration_days=3,
        cities=["Paris", "Lyon"],
        budget_total=2000.0,
        currency="EUR"
    )
    # Draft only visits Paris
    draft = _create_sample_draft(constraints, days_count=3, cities=["Paris"], total_cost=1500.0)

    agent = ReviewAgent()
    report = await agent.review(draft, constraints)

    assert report.overall_status == ReviewStatus.FAIL
    assert any("Missing cities" in msg for msg in report.blocking_issues)


@pytest.mark.asyncio
async def test_review_agent_budget_thresholds_ag007():
    """Verify ReviewAgent: <= 100% budget passes, 100%-102% is advisory, > 102% is blocking."""
    constraints = TravelConstraints(
        origin="LHR",
        destination_region="France",
        duration_days=3,
        cities=["Paris"],
        budget_total=1000.0,
        currency="EUR"
    )
    agent = ReviewAgent()

    # Case 1: 1010 EUR (1% over budget -> advisory warning, not blocking)
    draft_slight_over = _create_sample_draft(constraints, days_count=3, cities=["Paris"], total_cost=1010.0)
    report1 = await agent.review(draft_slight_over, constraints)
    assert report1.overall_status == ReviewStatus.WARNINGS
    assert len(report1.blocking_issues) == 0
    assert any("Budget" in msg for msg in report1.advisory_warnings)

    # Case 2: 1100 EUR (10% over budget -> blocking failure)
    draft_excessive_over = _create_sample_draft(constraints, days_count=3, cities=["Paris"], total_cost=1100.0)
    report2 = await agent.review(draft_excessive_over, constraints)
    assert report2.overall_status == ReviewStatus.FAIL
    assert any("Budget" in msg for msg in report2.blocking_issues)


@pytest.mark.asyncio
async def test_review_agent_layer2_qualitative_check():
    """Verify Layer 2 qualitative LLM check runs when Layer 1 programmatic checks pass."""
    mock_llm = MagicMock()
    mock_llm.chat_with_retry = AsyncMock(return_value="The itinerary pace is balanced with cultural focus.")

    constraints = TravelConstraints(
        origin="LHR",
        destination_region="France",
        duration_days=3,
        cities=["Paris"],
        budget_total=1500.0,
        currency="EUR",
        preferences=["art", "gastronomy"]
    )
    draft = _create_sample_draft(constraints, days_count=3, cities=["Paris"], total_cost=1200.0)

    agent = ReviewAgent(llm_client=mock_llm)
    report = await agent.review(draft, constraints)

    assert report.overall_status == ReviewStatus.PASS
    assert report.qualitative_assessment is not None
    assert "pace is balanced" in report.qualitative_assessment
