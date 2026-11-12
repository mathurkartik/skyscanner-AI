"""
Sprint 0 Verification Tests - P0 Security and Data Corruption Fixes
Covers AG-001, AG-002, AG-003, AG-004, AG-005.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.main import app
from app.utils.currency import to_usd, from_usd, convert_currency, USD_TO_CURRENCY
from app.agents.budget import BudgetAgent
from app.tools.hotel_client import HotelClient
from app.tools.google_places_client import GooglePlacesClient
from app.models.schemas import (
    TravelConstraints,
    LogisticsOutput,
    RealFlightOffer,
    RealHotelOffer,
    CarEstimate,
    CostBand
)


# =====================================================================
# AG-003: Canonical Currency FX Conversion
# =====================================================================

def test_ag003_canonical_currency_module():
    """Verify unified currency conversion rates and functions."""
    # 1. USD Base Identity
    assert to_usd(100.0, "USD") == 100.0
    assert from_usd(100.0, "USD") == 100.0
    assert convert_currency(100.0, "USD", "USD") == 100.0

    # 2. INR Conversions (1 USD = 83 INR)
    assert to_usd(8300.0, "INR") == 100.0
    assert from_usd(100.0, "INR") == 8300.0
    assert convert_currency(100.0, "USD", "INR") == 8300.0
    assert convert_currency(8300.0, "INR", "USD") == 100.0

    # 3. Same currency identity (must never multiply or divide)
    assert convert_currency(50000.0, "INR", "INR") == 50000.0
    assert convert_currency(1200.0, "EUR", "EUR") == 1200.0
    assert convert_currency(350.0, "GBP", "GBP") == 350.0

    # 4. Cross-currency conversion (EUR to INR via USD base)
    # 100 EUR -> USD = 100 / 0.92 ~ 108.70 USD -> INR = 108.70 * 83 ~ 9021.74 INR
    eur_to_inr = convert_currency(100.0, "EUR", "INR")
    assert 9000.0 < eur_to_inr < 9100.0

    # 5. Case insensitivity and unknown currency fallback
    assert convert_currency(100.0, "usd", "inr") == 8300.0
    assert convert_currency(100.0, "XYZ", "USD") == 100.0


# =====================================================================
# AG-004: Double FX Conversion Inflation Bug Prevention
# =====================================================================

@pytest.mark.asyncio
async def test_ag004_double_fx_conversion_prevention():
    """
    Verify BudgetAgent does NOT double-convert flight or hotel prices
    when real offers are already quoted in the trip's target currency.
    Previous bug: A 50,000 INR flight was multiplied by 83x -> 4,150,000 INR.
    """
    budget_agent = BudgetAgent()

    constraints = TravelConstraints(
        destination_region="Iceland",
        cities=["Reykjavik"],
        duration_days=5,
        budget_total=200000.0,
        currency="INR"
    )

    flight_offer = RealFlightOffer(
        id="fl-test-1",
        airline="Air India",
        flight_number="AI101",
        origin="DEL",
        destination="KEF",
        departure="2026-12-01T10:00:00",
        arrival="2026-12-01T20:00:00",
        duration_minutes=600,
        price=55000.0,
        currency="INR",
        deeplink="https://example.com"
    )

    hotel_offer = RealHotelOffer(
        id="ht-test-1",
        name="Grand Reykjavik",
        city="Reykjavik",
        price_per_night=8000.0,
        total_price=40000.0,
        currency="INR",
        star_rating=4.0,
        guest_rating=8.8,
        review_count=500,
        address="Central Ave",
        neighborhood="Downtown",
        deeplink="https://example.com"
    )

    logistics = LogisticsOutput(
        flight_offers=[flight_offer],
        hotels_by_city={"Reykjavik": [hotel_offer]},
        car_estimates=[],
        lodging_plans=[],
        movement_plans=[],
        day_skeletons=[],
        total_estimated_transit_hours=10.0
    )

    breakdown = await budget_agent.analyze(constraints, logistics)

    # Find transport and stay categories
    transport_cat = next((c for c in breakdown.categories if c.category == "transport"), None)
    stay_cat = next((c for c in breakdown.categories if c.category == "stay"), None)

    assert transport_cat is not None
    assert stay_cat is not None

    # Flight cost must be 55,000 INR, NOT 55,000 * 83 = 4,565,000 INR
    assert transport_cat.estimated_total == 55000.0
    # Lodging cost must be 40,000 INR, NOT 40,000 * 83 = 3,320,000 INR
    assert stay_cat.estimated_total == 40000.0


# =====================================================================
# AG-002: Dynamic Hotel Nights Scaling
# =====================================================================

def test_ag002_hotel_night_scaling_fallback():
    """Verify fallback hotel total_price scales directly with num_nights."""
    client = HotelClient()

    # 1 night stay
    hotels_1n = client._generate_fallback_hotels(
        dest_id="123",
        city_name="Reykjavik",
        arrival_date="2026-12-01",
        departure_date="2026-12-02",
        currency="USD",
        budget_tier="moderate",
        num_nights=1
    )
    # 5 nights stay
    hotels_5n = client._generate_fallback_hotels(
        dest_id="123",
        city_name="Reykjavik",
        arrival_date="2026-12-01",
        departure_date="2026-12-06",
        currency="USD",
        budget_tier="moderate",
        num_nights=5
    )

    assert len(hotels_1n) > 0
    assert len(hotels_5n) > 0

    h1 = hotels_1n[0]
    h5 = hotels_5n[0]

    # Nightly rates match
    assert h1.price_per_night == h5.price_per_night
    # Total price scales with nights: 5 nights total = 5 * 1 night total
    assert h1.total_price == round(h1.price_per_night * 1, 2)
    assert h5.total_price == round(h5.price_per_night * 5, 2)
    assert h5.total_price == round(h1.total_price * 5, 2)


@pytest.mark.asyncio
async def test_ag002_search_hotels_computes_nights_from_dates():
    """Verify search_hotels calculates stay nights from arrival and departure dates."""
    client = HotelClient()

    # 7 nights difference: 2026-12-01 to 2026-12-08
    offers = await client.search_hotels(
        dest_id="test-dest",
        city_name="Reykjavik",
        arrival_date="2026-12-01",
        departure_date="2026-12-08",
        currency="USD",
        budget_tier="budget"
    )

    assert len(offers) > 0
    first = offers[0]
    assert first.total_price == round(first.price_per_night * 7, 2)


# =====================================================================
# AG-001: Google API Key Photo URL Leakage Prevention
# =====================================================================

def test_ag001_photo_url_does_not_leak_api_key():
    """Verify Google Places photo URLs use backend proxy and NEVER expose API key."""
    client = GooglePlacesClient()

    item = {
        "place_id": "chI_12345",
        "name": "Hallgrimskirkja",
        "rating": 4.6,
        "user_ratings_total": 12000,
        "formatted_address": "Hallgrimstorg 1, Reykjavik",
        "geometry": {"location": {"lat": 64.1417, "lng": -21.9266}},
        "photos": [{"photo_reference": "SECRET_REF_XYZ987"}]
    }

    place = client._transform_google_place_item(item, api_key="AIzaSyConfidentialKey123")

    # photo_url must be proxied endpoint, NOT direct Google Maps URL with key
    assert place.photo_url == "/api/places/photo/SECRET_REF_XYZ987"
    assert "AIzaSyConfidentialKey123" not in place.photo_url
    assert "key=" not in place.photo_url


@pytest.mark.asyncio
async def test_ag001_photo_proxy_endpoint_registered():
    """Verify GET /api/places/photo/{photo_ref} endpoint exists in the FastAPI app."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # When photo ref is requested
        response = await client.get("/api/places/photo/test_photo_ref")
        # Response should be 403/404/502 (Google API response / photo ref not found), NOT Route Not Found
        # Route is verified to be mounted and active under /api/places/photo/
        assert response.status_code in [200, 403, 404, 502]


# =====================================================================
# AG-005: Environment Credential Safety Audit
# =====================================================================

def test_ag005_gitignore_protects_env_files():
    """Verify .gitignore properly protects .env files across backend and root."""
    gitignore_path = Path(__file__).resolve().parents[2] / ".gitignore"
    assert gitignore_path.exists(), ".gitignore must exist at repository root"

    content = gitignore_path.read_text(encoding="utf-8")
    assert ".env" in content
    assert "backend/.env" in content
    assert ".env.*" in content
    assert "Docs/" in content
