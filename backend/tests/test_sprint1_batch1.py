"""
Sprint 1 Batch 1 Verification Tests
Covers:
- AG-006: Review Agent qualitative audit calling LLM with fallback
- AG-007: Review Agent budget blocking threshold lowered to 102%
- AG-008: Holistic combined 70% cap for flights + lodging
- AG-019: Real flight prices preserved without silent reduction
- AG-020: DayItinerary floating-point validation tolerance
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.review import ReviewAgent
from app.agents.budget import BudgetAgent
from app.models.schemas import (
    TravelConstraints,
    DraftItinerary,
    DayItinerary,
    DayItineraryItem,
    ActivityType,
    LogisticsOutput,
    RealFlightOffer,
    RealHotelOffer,
    SuggestedSwap,
    BudgetBreakdown,
    BudgetCategory,
    ReviewSeverity,
    ReviewStatus
)


def _make_dummy_breakdown(total: float = 100.0, currency: str = "USD") -> BudgetBreakdown:
    """Helper to build a valid BudgetBreakdown satisfying Pydantic schema."""
    return BudgetBreakdown(
        categories=[BudgetCategory(category="stay", estimated_total=total, currency=currency)],
        grand_total=total,
        currency=currency,
        within_budget=True,
        remaining_buffer=0.0
    )


# =====================================================================
# AG-006: Review Agent Qualitative Check LLM Execution & Fallback
# =====================================================================

@pytest.mark.asyncio
async def test_ag006_review_agent_calls_llm_when_available():
    """Verify ReviewAgent._llm_qualitative_check invokes chat_with_retry."""
    mock_llm = MagicMock()
    mock_llm.chat_with_retry = AsyncMock(return_value="The itinerary pace is balanced with authentic dining.")

    agent = ReviewAgent(llm_client=mock_llm)
    constraints = TravelConstraints(
        destination_region="Japan",
        cities=["Tokyo", "Kyoto"],
        duration_days=2,
        budget_total=2000.0,
        currency="USD",
        preferences=["food", "culture"]
    )
    dummy_breakdown = _make_dummy_breakdown(35.0)
    draft = DraftItinerary(
        constraints=constraints,
        days=[
            DayItinerary(
                day_number=1,
                city="Tokyo",
                items=[DayItineraryItem(slot_index=0, time="10:00", activity_id="a1", activity_name="Senso-ji Temple", city="Tokyo", type=ActivityType.CULTURE, cost_estimate=20.0)],
                day_summary="Explore Asakusa",
                day_cost=20.0
            ),
            DayItinerary(
                day_number=2,
                city="Kyoto",
                items=[DayItineraryItem(slot_index=0, time="10:00", activity_id="a2", activity_name="Fushimi Inari", city="Kyoto", type=ActivityType.CULTURE, cost_estimate=15.0)],
                day_summary="Torii gates",
                day_cost=15.0
            )
        ],
        total_estimated_cost=35.0,
        currency="USD",
        budget_summary=dummy_breakdown
    )

    assessment = await agent._llm_qualitative_check(draft, constraints)

    # Must invoke LLM chat_with_retry
    assert mock_llm.chat_with_retry.called
    assert assessment == "The itinerary pace is balanced with authentic dining."


@pytest.mark.asyncio
async def test_ag006_review_agent_fallback_when_no_llm():
    """Verify ReviewAgent falls back gracefully to structured assessment when LLM is unavailable."""
    agent = ReviewAgent(llm_client=None)
    constraints = TravelConstraints(
        destination_region="Japan",
        cities=["Tokyo"],
        duration_days=1,
        budget_total=1000.0,
        currency="USD",
        preferences=["ramen", "food"]
    )
    draft = DraftItinerary(
        constraints=constraints,
        days=[
            DayItinerary(
                day_number=1,
                city="Tokyo",
                items=[DayItineraryItem(slot_index=0, time="12:00", activity_id="a1", activity_name="Ramen Tasting Tour", city="Tokyo", type=ActivityType.FOOD, cost_estimate=40.0)],
                day_summary="Culinary discovery",
                day_cost=40.0
            )
        ],
        total_estimated_cost=40.0,
        currency="USD",
        budget_summary=_make_dummy_breakdown(40.0)
    )

    assessment = await agent._llm_qualitative_check(draft, constraints)
    assert assessment is not None
    assert "Itinerary covers 1 days" in assessment
    assert "Tokyo" in assessment


# =====================================================================
# AG-007: Review Agent Budget Threshold (102% Blocking)
# =====================================================================

def test_ag007_review_budget_blocking_threshold():
    """
    Verify budget overage above 102% is marked BLOCKING,
    and 100-102% is marked ADVISORY.
    Previous bug: Up to 110% was only ADVISORY, allowing $500 silent overages.
    """
    agent = ReviewAgent()
    constraints = TravelConstraints(
        destination_region="Iceland",
        cities=["Reykjavik"],
        duration_days=3,
        budget_total=5000.0,
        currency="USD"
    )

    # 1. Exact or under budget -> passed=True
    draft_ok = DraftItinerary(
        constraints=constraints,
        days=[],
        total_estimated_cost=4900.0,
        currency="USD",
        budget_summary=_make_dummy_breakdown(4900.0)
    )
    checks_ok = agent._check_budget(draft_ok, constraints)
    assert checks_ok[0].passed is True
    assert checks_ok[0].severity == ReviewSeverity.ADVISORY

    # 2. 1% over budget ($5,050 vs $5,000) -> ADVISORY, passed=False
    draft_minor_over = DraftItinerary(
        constraints=constraints,
        days=[],
        total_estimated_cost=5050.0,
        currency="USD",
        budget_summary=_make_dummy_breakdown(5050.0)
    )
    checks_minor = agent._check_budget(draft_minor_over, constraints)
    assert checks_minor[0].passed is False
    assert checks_minor[0].severity == ReviewSeverity.ADVISORY

    # 3. 3% over budget ($5,150 vs $5,000) -> BLOCKING, passed=False (triggers repair)
    draft_blocking = DraftItinerary(
        constraints=constraints,
        days=[],
        total_estimated_cost=5150.0,
        currency="USD",
        budget_summary=_make_dummy_breakdown(5150.0)
    )
    checks_blocking = agent._check_budget(draft_blocking, constraints)
    assert checks_blocking[0].passed is False
    assert checks_blocking[0].severity == ReviewSeverity.BLOCKING


# =====================================================================
# AG-019 & AG-008: Budget Real Flight Preservation & Combined 70% Cap
# =====================================================================

@pytest.mark.asyncio
async def test_ag019_real_flight_price_preserved():
    """
    AG-019: Real flight prices are NOT silently reduced to 35% of total budget
    when exceeding 50%. Real quote is kept and budget concerns are flagged.
    """
    agent = BudgetAgent()
    constraints = TravelConstraints(
        destination_region="Iceland",
        cities=["Reykjavik"],
        duration_days=4,
        budget_total=1000.0,
        currency="USD"
    )
    flight = RealFlightOffer(
        id="fl-real-1",
        airline="Icelandair",
        flight_number="FI101",
        origin="JFK",
        destination="KEF",
        departure="2026-12-01T08:00:00",
        arrival="2026-12-01T18:00:00",
        duration_minutes=360,
        price=650.0,  # 65% of $1,000 budget
        currency="USD"
    )
    logistics = LogisticsOutput(
        flight_offers=[flight],
        hotels_by_city={},
        car_estimates=[],
        lodging_plans=[],
        movement_plans=[],
        day_skeletons=[],
        total_estimated_transit_hours=6.0
    )

    breakdown = await agent.analyze(constraints, logistics)
    transport_cat = next(c for c in breakdown.categories if c.category == "transport")

    # Price must remain $650.00 and NOT be silently reduced to $350.00
    assert transport_cat.estimated_total == 650.0
    assert "exceed 50%" in transport_cat.notes


@pytest.mark.asyncio
async def test_ag008_combined_cap_allocates_discretionary():
    """
    AG-008: Flights + Hotels share a holistic 70% cap, leaving at least 30%
    for food, activities, and buffer when under the cap.
    """
    agent = BudgetAgent()
    constraints = TravelConstraints(
        destination_region="Iceland",
        cities=["Reykjavik"],
        duration_days=3,
        budget_total=1000.0,
        currency="USD"
    )
    flight = RealFlightOffer(
        id="fl-real-2",
        airline="Icelandair",
        flight_number="FI102",
        origin="BOS",
        destination="KEF",
        departure="2026-12-01T08:00:00",
        arrival="2026-12-01T18:00:00",
        duration_minutes=360,
        price=350.0,  # 35%
        currency="USD"
    )
    hotel = RealHotelOffer(
        id="ht-real-1",
        name="Reykjavik Hotel",
        city="Reykjavik",
        price_per_night=100.0,
        total_price=300.0,  # 30% (combined 65% <= 70% cap)
        currency="USD"
    )
    logistics = LogisticsOutput(
        flight_offers=[flight],
        hotels_by_city={"Reykjavik": [hotel]},
        car_estimates=[],
        lodging_plans=[],
        movement_plans=[],
        day_skeletons=[],
        total_estimated_transit_hours=6.0
    )

    breakdown = await agent.analyze(constraints, logistics)
    cat_map = {c.category: c.estimated_total for c in breakdown.categories}

    assert cat_map["transport"] == 350.0
    assert cat_map["stay"] == 300.0
    # Remaining $350 (35% > 30% min) distributed to food, activities, buffer
    discretionary = cat_map["food"] + cat_map["activities"] + cat_map["buffer"]
    assert round(discretionary, 2) == 350.0
    assert breakdown.grand_total == 1000.0
    assert breakdown.within_budget is True


# =====================================================================
# AG-020: DayItinerary Floating Point Validator Tolerance
# =====================================================================

def test_ag020_day_itinerary_validator_tolerance():
    """
    AG-020: DayItinerary permits small floating-point / rounding variances
    up to $5.00 without raising a ValueError.
    """
    # 3 items summing to $82.35, day_cost set to $85.00 ($2.65 difference, was rejected by $1.00 tolerance)
    day = DayItinerary(
        day_number=1,
        city="Rome",
        items=[
            DayItineraryItem(slot_index=0, time="09:00", activity_id="i1", activity_name="Colosseum", city="Rome", type=ActivityType.MUSEUM, cost_estimate=32.10),
            DayItineraryItem(slot_index=1, time="13:00", activity_id="i2", activity_name="Trastevere Lunch", city="Rome", type=ActivityType.FOOD, cost_estimate=25.15),
            DayItineraryItem(slot_index=2, time="16:00", activity_id="i3", activity_name="Pantheon", city="Rome", type=ActivityType.CULTURE, cost_estimate=25.10)
        ],
        day_summary="Ancient Rome exploration",
        day_cost=85.0  # 85.0 vs 82.35 calculated (delta $2.65 <= $5.00 tolerance)
    )

    assert day.day_cost == 85.0

    # Gross discrepancy ($150 vs $82.35) must still be rejected
    with pytest.raises(ValueError) as excinfo:
        DayItinerary(
            day_number=2,
            city="Rome",
            items=[
                DayItineraryItem(slot_index=0, time="09:00", activity_id="i1", activity_name="Vatican", city="Rome", type=ActivityType.MUSEUM, cost_estimate=32.10)
            ],
            day_summary="Vatican City",
            day_cost=150.0  # $117.90 discrepancy
        )
    assert "doesn't match sum of items" in str(excinfo.value)
