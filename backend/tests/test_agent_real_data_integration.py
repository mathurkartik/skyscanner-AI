"""
Phase 5 Integration Tests: Verifies that Orchestrator, Logistics, Destination,
and Budget agents produce itineraries enriched with real flight quotes,
real hotel offers, Google Places attractions, car estimates, and map pins.
"""

import pytest
from app.agents.orchestrator import OrchestratorAgent
from app.models.schemas import TravelConstraints, FinalItinerary


@pytest.mark.asyncio
async def test_orchestrator_iceland_road_trip_real_data():
    """
    Exit criteria for Phase 5:
    'Plan an 11-day Iceland road trip, ₹3.5L budget' returns itinerary with
    real hotel names/prices, real flight prices, and real attraction ratings.
    """
    orchestrator = OrchestratorAgent()

    constraints = TravelConstraints(
        destination_region="Iceland",
        cities=["Reykjavik", "Vík", "Akureyri"],
        duration_days=11,
        budget_total=350000,
        currency="INR",
        is_road_trip=True,
        preferences=["road trip", "waterfalls", "geothermal spas"],
        avoidances=["rush"]
    )

    # 1. Run Destination Agent
    activity_catalog = await orchestrator.destination_agent.research(constraints)
    assert len(activity_catalog.activities) > 0
    assert "Reykjavik" in activity_catalog.places_by_city or "Vík" in activity_catalog.places_by_city

    # 2. Run Logistics Agent (queries real flights, hotels, car estimates)
    logistics_output = await orchestrator.logistics_agent.plan(constraints, activity_catalog)
    assert len(logistics_output.flight_offers) > 0
    assert logistics_output.flight_offers[0].destination == "KEF"
    assert len(logistics_output.hotels_by_city) > 0
    assert "Reykjavik" in logistics_output.hotels_by_city
    assert len(logistics_output.hotels_by_city["Reykjavik"]) > 0
    assert len(logistics_output.car_estimates) >= 2  # Has SUV 4x4 and Campervan for road trip

    # 3. Run Budget Agent (calibrated with real quotes)
    budget_breakdown = await orchestrator.budget_agent.analyze(constraints, logistics_output)
    assert budget_breakdown.grand_total > 0
    assert len(budget_breakdown.categories) > 0

    # 4. Merge outputs
    draft = await orchestrator.merge(
        constraints=constraints,
        activity_catalog=activity_catalog,
        logistics_output=logistics_output,
        budget_breakdown=budget_breakdown
    )
    assert len(draft.days) == 11
    # Check that day 1 has hotel options and places
    assert len(draft.days[0].hotel_options) > 0
    assert draft.days[0].hotel_options[0].name != ""
    assert len(draft.days[0].places) > 0

    # 5. Final Output Conversion
    final = orchestrator._draft_to_final(
        draft=draft,
        constraints=constraints,
        budget_breakdown=budget_breakdown
    )

    assert isinstance(final, FinalItinerary)
    assert len(final.flight_options) > 0
    assert len(final.car_estimates) > 0
    assert len(final.map_pins) > 0
    assert any(pin.pin_type == "airport" for pin in final.map_pins)
    assert any(pin.pin_type == "overnight" for pin in final.map_pins)
    assert len(final.cost_saving_tips_v2) >= 3


@pytest.mark.asyncio
async def test_logistics_hotel_swap_suggestion():
    """Verify that Budget Agent generates hotel swap suggestions from real Booking.com inventory."""
    orchestrator = OrchestratorAgent()

    constraints = TravelConstraints(
        destination_region="Iceland",
        cities=["Reykjavik"],
        duration_days=4,
        budget_total=80000,
        currency="INR"
    )

    activity_catalog = await orchestrator.destination_agent.research(constraints)
    logistics_output = await orchestrator.logistics_agent.plan(constraints, activity_catalog)
    budget_breakdown = await orchestrator.budget_agent.analyze(constraints, logistics_output)

    # If multiple hotels exist in Reykjavik, a swap should be suggested
    if len(logistics_output.hotels_by_city.get("Reykjavik", [])) > 1:
        assert len(budget_breakdown.suggested_swaps) > 0

