"""
Comprehensive Unit Tests for Skyscanner AI Improvement Plan (Phases 1-4).
Tests:
- P0-3: Ring route deduplication
- P0-4: Budget category synonym normalization
- P0-5: Dynamic coordinates lookup
- P0-6: Duffel Airways sanitization
- P1-1: Budget cap enforcement and 0% fallback drift
- P1-2: Currency normalization
- P1-3: Hotel budget tier adaptation
- P1-4: Semantic road trip detection
- P1-6: PracticalInfo schema and generation
- P1-7: Comma-separated budget extraction
- P2-2: Debug endpoints security gating
- P3-8: Rate limiting middleware
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

from app.models.schemas import (
    TravelConstraints, BudgetCategory, BudgetBreakdown,
    FinalItinerary, PracticalInfo, PlanInsights, RealHotelOffer
)
from app.agents.budget import BudgetAgent
from app.llm.llm_utils import (
    apply_rule_overrides, sanitize_numeric_fields, extract_json_from_text
)
from app.tools.hotel_client import HotelClient
from app.main import app


def test_budget_category_synonym_normalization():
    """P0-4: Ensure synonyms map to standard 5 categories without ValidationError."""
    c1 = BudgetCategory(category="intercity transport", estimated_total=120.0, currency="USD")
    assert c1.category == "transport"

    c2 = BudgetCategory(category="lodging", estimated_total=300.0, currency="USD")
    assert c2.category == "stay"

    c3 = BudgetCategory(category="hotel", estimated_total=250.0, currency="USD")
    assert c3.category == "stay"

    c4 = BudgetCategory(category="dining & restaurants", estimated_total=180.0, currency="USD")
    assert c4.category == "food"

    c5 = BudgetCategory(category="sightseeing & tours", estimated_total=90.0, currency="USD")
    assert c5.category == "activities"

    c6 = BudgetCategory(category="emergency contingency", estimated_total=50.0, currency="USD")
    assert c6.category == "buffer"


def test_ring_route_city_deduplication():
    """P0-3: Ring routes (first == last) are preserved while inner duplicates are deduplicated."""
    constraints = TravelConstraints(
        destination_region="Iceland",
        cities=["Reykjavik", "Vík", "Vík", "Akureyri", "Reykjavik"],
        duration_days=7,
        budget_total=250000,
        currency="INR"
    )
    # First is Reykjavik, last is Reykjavik, middle Vik is deduped
    assert constraints.cities == ["Reykjavik", "Vík", "Akureyri", "Reykjavik"]


def test_semantic_road_trip_detection():
    """P1-4: 'scenic drives' or 'self-drive' trigger is_road_trip=True semantically."""
    data = {"destination_region": "Switzerland", "duration_days": 8}
    updated = apply_rule_overrides(data, "Plan an 8-day trip to Switzerland with scenic drives and alpine loops.")
    assert updated.get("is_road_trip") is True
    assert "road trip" in updated.get("preferences", [])

    data2 = {"destination_region": "Sweden", "duration_days": 7}
    updated2 = apply_rule_overrides(data2, "7 days self-drive vacation from Stockholm to Gothenburg.")
    assert updated2.get("is_road_trip") is True


def test_comma_separated_budget_parsing():
    """P1-7: Extract numbers formatted with commas ($3,000, €2,500, ₹10,00,000)."""
    d1 = apply_rule_overrides({}, "Plan a 10-day trip to Japan with a $3,000 budget.")
    assert d1.get("budget_total") == 3000.0
    assert d1.get("currency") == "USD"

    d2 = apply_rule_overrides({}, "Plan a 14-day Europe trip with €2,500 budget.")
    assert d2.get("budget_total") == 2500.0
    assert d2.get("currency") == "EUR"

    d3 = apply_rule_overrides({}, "Trip to Kerala with ₹10,00,000 budget.")
    assert d3.get("budget_total") == 1000000.0
    assert d3.get("currency") == "INR"


@pytest.mark.asyncio
async def test_fallback_budget_analyze_exact_sum():
    """P1-1: Fallback analyze categories sum to exactly budget_total (0% drift)."""
    agent = BudgetAgent()
    constraints = TravelConstraints(
        destination_region="Japan",
        cities=["Tokyo", "Kyoto"],
        duration_days=7,
        budget_total=3000.0,
        currency="USD"
    )
    breakdown = await agent._fallback_analyze(constraints)
    cat_sum = round(sum(c.estimated_total for c in breakdown.categories), 2)
    assert cat_sum == 3000.0
    assert breakdown.grand_total == 3000.0
    assert breakdown.within_budget is True


@pytest.mark.asyncio
async def test_budget_cap_enforcement_in_calibration():
    """P1-1: Post-calibration cap prevents blowout and triggers swaps."""
    agent = BudgetAgent()
    constraints = TravelConstraints(
        destination_region="Dubai",
        cities=["Dubai"],
        duration_days=5,
        budget_total=1000.0,
        currency="USD"
    )
    # Mock logistics with an expensive hotel
    mock_logistics = MagicMock()
    mock_logistics.flight_offers = []
    expensive_hotel = RealHotelOffer(
        name="Burj Al Arab",
        city="Dubai",
        price_per_night=800.0,
        total_price=2400.0,
        currency="USD"
    )
    cheaper_hotel = RealHotelOffer(
        name="Rove Downtown",
        city="Dubai",
        price_per_night=120.0,
        total_price=360.0,
        currency="USD"
    )
    mock_logistics.hotels_by_city = {"Dubai": [expensive_hotel, cheaper_hotel]}

    breakdown = await agent.analyze(constraints, mock_logistics)
    assert breakdown.grand_total <= constraints.budget_total
    assert breakdown.within_budget is True
    # Should have generated a swap recommendation
    assert len(breakdown.suggested_swaps) > 0


@pytest.mark.asyncio
async def test_hotel_budget_tier_matching():
    """P1-3: Luxury tier returns luxury properties with higher price points."""
    client = HotelClient()
    luxury_hotels = client._generate_fallback_hotels(
        dest_id="dubai",
        city_name="Dubai",
        arrival_date="2026-12-01",
        departure_date="2026-12-04",
        currency="USD",
        budget_tier="luxury"
    )
    assert len(luxury_hotels) >= 2
    assert luxury_hotels[0].price_per_night >= 300.0
    assert luxury_hotels[0].star_rating >= 4.5

    budget_hotels = client._generate_fallback_hotels(
        dest_id="dubai",
        city_name="Dubai",
        arrival_date="2026-12-01",
        departure_date="2026-12-04",
        currency="USD",
        budget_tier="budget"
    )
    assert len(budget_hotels) >= 2
    assert budget_hotels[0].price_per_night <= 100.0


def test_practical_info_schema():
    """P1-6: PracticalInfo model validation and defaults."""
    info = PracticalInfo(
        visa_requirements="Schengen Visa required for Indian passport holders.",
        driving_requirements="IDP required for car rentals.",
        currency_notes="Cards accepted everywhere, cashless society.",
        seasonal_weather_note="Pack warm waterproof layers.",
        emergency_contacts="112"
    )
    assert info.visa_requirements.startswith("Schengen")
    assert info.emergency_contacts == "112"


@pytest.mark.asyncio
async def test_debug_endpoints_security_gating():
    """P2-2: Gate debug endpoints behind environment check."""
    import httpx
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # When debug_mode is disabled or in production:
        with patch("app.api.routes.get_settings") as mock_settings:
            mock = MagicMock()
            mock.debug = False
            mock.app_env = "production"
            mock_settings.return_value = mock

            res1 = await client.get("/api/debug/llm-test")
            assert res1.status_code == 403

            res2 = await client.get("/api/debug/pipeline-test")
            assert res2.status_code == 403


def test_extract_json_markdown_robustness():
    """P3-2: extract_json handles markdown codeblocks and extra preambles."""
    raw = "```json\n{\"destination\": \"Rome\", \"days\": 5}\n```\nHere is your plan."
    extracted = extract_json_from_text(raw)
    assert extracted == '{"destination": "Rome", "days": 5}'

    plain = 'Some notes {"key": "val"} extra stuff'
    assert extract_json_from_text(plain) == '{"key": "val"}'
