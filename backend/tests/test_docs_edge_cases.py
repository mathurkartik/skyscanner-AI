"""
Edge Cases Test Suite based on Docs specifications:
- Docs/improvement.md: Zero-hardcoding, dynamic LLM stack, resilient dual-provider
- Docs/improvement_v1.md: Empty flights/hotels/pins/budget categories defense
- Docs/improvement_v2.md: Origin city handling, multi-modal transport segments
- Docs/improvement_v3.md: Dynamic IATA resolution, zero static dictionaries
- Docs/IntegrationArchitecture.md: 3-pillar validation, Booking & Skyscanner integration

Covers 10 critical edge cases and failure modes identified across documentation.
"""

import pytest
from pydantic import ValidationError
from app.agents.orchestrator import OrchestratorAgent, fix_utf8
from app.agents.budget import BudgetAgent
from app.tools.flight_client import FlightClient, resolve_iata, resolve_iata_sync
from app.tools.hotel_client import HotelClient
from app.tools.google_places_client import GooglePlacesClient
from app.models.exceptions import MissingConstraintError
from app.models.schemas import (
    TravelConstraints,
    LogisticsOutput,
    RealFlightOffer,
    RealHotelOffer,
    TransportSegment,
)


# ============================================================================
# Edge Case 1: Strict 3-Pillar Pre-Flight Validation Failures
# ============================================================================

def test_edge_case_missing_budget_pillar():
    """Docs/improvement.md: Destination + Duration provided, but NO budget -> must raise MissingConstraintError."""
    orchestrator = OrchestratorAgent()
    constraints = TravelConstraints(
        destination_region="Tokyo, Japan",
        duration_days=7,
        budget_total=None,
        budget_tier=None,
        currency="USD"
    )
    with pytest.raises(MissingConstraintError) as exc_info:
        orchestrator.validate_constraints(constraints)
    assert "budget" in exc_info.value.missing_fields
    assert "destination" not in exc_info.value.missing_fields
    assert "duration" not in exc_info.value.missing_fields


def test_edge_case_missing_destination_and_duration():
    """Docs/improvement.md: Budget provided, but NO destination or duration -> must raise for both."""
    orchestrator = OrchestratorAgent()
    constraints = TravelConstraints(
        destination_region="",
        duration_days=None,
        budget_total=2500,
        currency="USD"
    )
    with pytest.raises(MissingConstraintError) as exc_info:
        orchestrator.validate_constraints(constraints)
    assert "destination" in exc_info.value.missing_fields
    assert "duration" in exc_info.value.missing_fields
    assert "budget" not in exc_info.value.missing_fields


def test_edge_case_missing_all_three_pillars():
    """Docs/improvement.md: Vague input ('Plan a relaxing trip') -> must flag all 3 pillars."""
    orchestrator = OrchestratorAgent()
    constraints = TravelConstraints(
        destination_region=None,
        duration_days=None,
        budget_total=None,
        budget_tier=None
    )
    with pytest.raises(MissingConstraintError) as exc_info:
        orchestrator.validate_constraints(constraints)
    assert set(exc_info.value.missing_fields) == {"destination", "duration", "budget"}


# ============================================================================
# Edge Case 2: Budget Tier Benchmark Auto-Calculation
# ============================================================================

def test_edge_case_budget_tier_auto_calibration():
    """
    Docs/improvement.md & Orchestrator:
    When user specifies budget tier ('budget', 'mid', 'luxury') without exact amount,
    system calibrates a realistic benchmark total based on region and duration.
    """
    orchestrator = OrchestratorAgent()
    constraints = TravelConstraints(
        destination_region="Iceland",
        duration_days=7,
        budget_total=None,
        budget_tier="budget",
        currency="EUR"
    )
    validated = orchestrator.validate_constraints(constraints)
    assert validated.budget_total is not None
    assert validated.budget_total > 0
    # Realistic calibrated benchmark for 7 days in EUR
    assert 300 <= validated.budget_total <= 2500


# ============================================================================
# Edge Case 3: Duration Boundaries (Zero, Negative)
# ============================================================================

def test_edge_case_zero_or_negative_duration():
    """Docs: Duration of 0 or negative days must be caught by validation."""
    with pytest.raises((MissingConstraintError, ValidationError)):
        TravelConstraints(
            destination_region="Paris",
            duration_days=0,
            budget_total=1500
        )


# ============================================================================
# Edge Case 4: Obscure / Secondary City IATA Airport Resolution
# ============================================================================

@pytest.mark.asyncio
async def test_edge_case_obscure_city_iata_resolution():
    """
    Docs/improvement.md Step 4:
    LLM knows secondary cities and maps to nearest major commercial airport:
    - Gandhinagar -> AMD (Ahmedabad) or DEL
    - Kyoto -> KIX (Osaka/Kansai) or ITM or HND
    """
    code_gandhinagar = await resolve_iata("Gandhinagar")
    assert code_gandhinagar in ["AMD", "DEL"]

    code_kyoto = await resolve_iata("Kyoto")
    assert code_kyoto in ["KIX", "ITM", "HND"]


@pytest.mark.asyncio
async def test_edge_case_raw_iata_codes_instant_resolution():
    """Direct 3-letter IATA codes (upper/lowercase) must resolve without calling LLM."""
    assert await resolve_iata("kef") == "KEF"
    assert await resolve_iata("LHR") == "LHR"
    assert await resolve_iata("DEL") == "DEL"
    assert resolve_iata_sync("KEF") == "KEF"
    assert resolve_iata_sync("jfk") == "JFK"


# ============================================================================
# Edge Case 5: Single-Night Hotel Stay (No Division by Zero)
# ============================================================================

@pytest.mark.asyncio
async def test_edge_case_hotel_single_night_stay():
    """
    Docs/improvement_v1.md:
    Ensure 1-night stay calculates price_per_night properly without division by zero.
    """
    client = HotelClient()
    offers = await client.search_hotels(
        dest_id="-12345",
        city_name="Reykjavik",
        arrival_date="2026-12-01",
        departure_date="2026-12-02",
        currency="USD"
    )
    assert len(offers) >= 2
    for h in offers:
        assert isinstance(h, RealHotelOffer)
        assert h.price_per_night > 0
        assert h.total_price > 0
        assert h.currency == "USD"


# ============================================================================
# Edge Case 6: Sparse / Rural Coordinates POI Generation
# ============================================================================

@pytest.mark.asyncio
async def test_edge_case_sparse_coordinates_attractions():
    """
    Docs/improvement.md:
    When searching coordinates in rural regions with no Google Places API hits,
    dynamic fallback must still return valid, non-empty PlaceInfo items with coordinates.
    """
    places_client = GooglePlacesClient()
    places = await places_client.search_nearby(
        lat=64.12,
        lng=-21.90,
        radius_m=10000,
        limit=4
    )
    assert len(places) >= 2
    for p in places:
        assert p.name is not None
        assert p.rating is not None and p.rating >= 4.0
        assert p.lat is not None
        assert p.lng is not None
        assert -90.0 <= p.lat <= 90.0
        assert -180.0 <= p.lng <= 180.0


# ============================================================================
# Edge Case 7: Multi-Currency Budget Rollup Consistency
# ============================================================================

@pytest.mark.asyncio
async def test_edge_case_budget_rollup_currency_and_sum_consistency():
    """
    Docs/improvement_v1.md:
    Budget categories must match the requested currency (e.g. JPY, INR, EUR)
    and the sum of categories must exactly equal grand_total.
    """
    budget_agent = BudgetAgent()
    constraints = TravelConstraints(
        destination_region="Japan",
        duration_days=5,
        budget_total=300000,
        currency="JPY"
    )
    dummy_logistics = LogisticsOutput(
        flight_offers=[
            RealFlightOffer(
                airline="ANA",
                airline_code="NH",
                flight_number="NH 828",
                origin="DEL",
                destination="HND",
                price=85000.0,
                currency="JPY",
                duration_minutes=420,
                stops=0,
                departure="19:00",
                arrival="06:30",
                deeplink="https://skyscanner.com",
                cabin_class="economy"
            )
        ],
        hotels_by_city={
            "Tokyo": [
                RealHotelOffer(
                    name="Tokyo Prince Hotel",
                    city="Tokyo",
                    price_per_night=18000.0,
                    total_price=72000.0,
                    currency="JPY",
                    star_rating=4.0,
                    guest_rating=8.6,
                    address="Minato City, Tokyo",
                    deeplink="https://booking.com"
                )
            ]
        },
        lodging_plans=[],
        movement_plans=[],
        day_skeletons=[],
        total_estimated_transit_hours=0.0
    )

    budget_breakdown = await budget_agent.analyze(constraints, dummy_logistics)
    assert budget_breakdown.currency == "JPY"
    assert budget_breakdown.grand_total > 0
    assert len(budget_breakdown.categories) >= 3

    # Exact sum check
    cat_sum = sum(c.estimated_total for c in budget_breakdown.categories)
    assert abs(cat_sum - budget_breakdown.grand_total) < 0.05


# ============================================================================
# Edge Case 8: UTF-8 Mojibake and Accent Repair
# ============================================================================

def test_edge_case_mojibake_and_accent_repair():
    """
    Docs/improvement_v1.md:
    Repair double-encoded UTF-8 characters (mojibake) in European/Nordic destination names.
    """
    # Double-encode UTF-8 string to simulate mojibake
    mojibake_reyk = "Reykjavík".encode("utf-8").decode("latin-1")
    mojibake_zurich = "Zürich".encode("utf-8").decode("latin-1")
    mojibake_sp = "São Paulo".encode("utf-8").decode("latin-1")

    assert fix_utf8(mojibake_reyk) == "Reykjavík"
    assert fix_utf8(mojibake_zurich) == "Zürich"
    assert fix_utf8(mojibake_sp) == "São Paulo"
    assert fix_utf8("Clean Plain Text") == "Clean Plain Text"
    assert fix_utf8(None) is None


# ============================================================================
# Edge Case 9: Multi-Modal Transport Segment Recommendation
# ============================================================================

def test_edge_case_transport_segment_model_validation():
    """
    Docs/improvement.md Multi-Modal:
    Ensure non-flight segments (e.g. Eurostar train, ferry) serialize with correct fields.
    """
    train_segment = TransportSegment(
        from_city="London",
        to_city="Paris",
        recommended_mode="train",
        reason="High-speed rail direct city center to center in 2h 15m",
        estimated_duration_hours=2.25,
        estimated_cost_usd=95.0,
        operator_name="Eurostar",
        line_or_flight_number="9012",
        booking_url="https://www.eurostar.com"
    )
    assert train_segment.recommended_mode == "train"
    assert train_segment.from_city == "London"
    assert train_segment.estimated_duration_hours == 2.25
    assert train_segment.operator_name == "Eurostar"


# ============================================================================
# Edge Case 10: Dynamic Fallback for Unknown Route Flights
# ============================================================================

@pytest.mark.asyncio
async def test_edge_case_flight_search_uncommon_route():
    """
    Docs/improvement.md:
    Searching an unusual route (e.g. Nuuk GOH to Tromso TOS) must produce
    valid RealFlightOffer items with Skyscanner booking links, realistic stops, and layovers.
    """
    client = FlightClient()
    offers = await client.search_flights(
        origin="GOH",
        destination="TOS",
        departure_date="2026-12-05",
        return_date="2026-12-15",
        cabin_class="economy",
        adults=1,
        currency="USD"
    )
    assert len(offers) >= 1
    offer = offers[0]
    assert isinstance(offer, RealFlightOffer)
    assert offer.origin == "GOH"
    assert offer.destination == "TOS"
    assert offer.price > 0
    assert offer.duration_minutes > 0
    assert "duffel.com" in offer.deeplink or "skyscanner.com" in offer.deeplink
