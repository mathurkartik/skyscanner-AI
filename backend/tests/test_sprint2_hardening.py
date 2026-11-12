"""
Unit tests for Sprint 2 Operational Hardening & Edge Cases (AG-081, AG-038, AG-039, AG-047, AG-048, AG-052, AG-053, AG-054, AG-055, AG-076).
"""

import pytest
import pytest_asyncio
import re
import httpx
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.config import settings
from app.agents.orchestrator import fix_utf8
from app.tools.destination_tips import get_destination_tips
from app.tools.router import ToolRouter
from app.agents.logistics import LogisticsAgent
from app.tools.hotel_client import HotelClient
from app.models.schemas import TravelConstraints, RealHotelOffer


@pytest_asyncio.fixture
async def async_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def test_fix_utf8_preserves_valid_portuguese_and_fixes_mojibake_ag052():
    """Verify fix_utf8 repairs double-encoded mojibake while preserving valid UTF-8 like 'SÃO PAULO'."""
    # Valid Portuguese uppercase Ã with tilde should NOT be corrupted
    valid_text = "Flight to SÃO PAULO with CONEXÃO"
    repaired_valid = fix_utf8(valid_text)
    assert repaired_valid == valid_text
    assert "SÃO PAULO" in repaired_valid

    # Double-encoded Mojibake: "CafÃ©" should be repaired to "Café"
    mojibake_text = "Visiting a Parisian CafÃ© and MusÃ©e"
    repaired_mojibake = fix_utf8(mojibake_text)
    assert repaired_mojibake == "Visiting a Parisian Café and Musée"


def test_destination_tips_regional_coverage_ag047():
    """Verify destination_tips returns authentic tips for major regions and falls back gracefully."""
    # France tips
    france_tips = get_destination_tips("France", ["Paris", "Nice"])
    assert len(france_tips) >= 3
    assert any("Navigo" in (t.title + " " + t.description) or "Louvre" in (t.title + " " + t.description) or "museum" in (t.title + " " + t.description).lower() for t in france_tips)

    # Japan tips
    japan_tips = get_destination_tips("Japan", ["Tokyo", "Kyoto"])
    assert len(japan_tips) >= 3
    assert any("Subway" in (t.title + " " + t.description) or "Shinkansen" in (t.title + " " + t.description) or "Rail" in (t.title + " " + t.description) or "bento" in (t.title + " " + t.description).lower() for t in japan_tips)

    # Iceland tips
    iceland_tips = get_destination_tips("Iceland", ["Reykjavik", "Vik"])
    assert len(iceland_tips) >= 3
    assert any("Bónus" in (t.title + " " + t.description) or "Geothermal" in (t.title + " " + t.description) or "Fuel" in (t.title + " " + t.description) for t in iceland_tips)

    # Unknown region fallback
    unknown_tips = get_destination_tips("UnknownCountry", ["CityA"])
    assert len(unknown_tips) >= 2


@pytest.mark.asyncio
async def test_book_endpoint_validation_ag076(async_client):
    """Verify /book validates user_name length and email format."""
    # Invalid: name too short
    resp_short_name = await async_client.post("/api/book", json={
        "user_name": "A",
        "user_email": "test@example.com",
        "item_type": "flight",
        "item_id": "fl-1"
    })
    assert resp_short_name.status_code == 400
    assert "Name is required" in resp_short_name.json()["detail"]

    # Invalid: malformed email
    resp_bad_email = await async_client.post("/api/book", json={
        "user_name": "John Doe",
        "user_email": "not-an-email",
        "item_type": "flight",
        "item_id": "fl-1"
    })
    assert resp_bad_email.status_code == 400
    assert "Valid email address is required" in resp_bad_email.json()["detail"]

    # Valid booking
    resp_valid = await async_client.post("/api/book", json={
        "user_name": "Jane Doe",
        "user_email": "jane@example.com",
        "item_type": "hotel",
        "item_id": "h-123"
    })
    assert resp_valid.status_code == 200
    data = resp_valid.json()
    assert data["status"] == "success"
    assert data["contact_email"] == settings.booking_contact_email


def test_router_cache_eviction_ag038():
    """Verify ToolRouter._set_cache bounds memory by evicting earliest entries when limit is reached."""
    router = ToolRouter()
    router.CACHE_MAX_ITEMS = 10  # temporary small limit for testing

    for i in range(15):
        router._set_cache(f"key_{i}", f"value_{i}")

    assert len(router._cache) <= 10
    # First 5 items (key_0 through key_4) must have been evicted
    assert "key_0" not in router._cache
    assert "key_14" in router._cache


def test_hotel_client_booking_search_url_ag054():
    """Verify HotelClient generates authentic Booking.com search URLs."""
    client_hotel = HotelClient()
    url = client_hotel.generate_booking_url(
        hotel_name="Grand Hotel",
        city="Paris",
        arrival="2026-06-01",
        departure="2026-06-05"
    )
    assert url.startswith("https://www.booking.com/searchresults.html?")
    assert "Grand+Hotel" in url or "Grand%20Hotel" in url
    assert "Paris" in url
    assert "checkin=2026-06-01" in url
    assert "checkout=2026-06-05" in url


@pytest.mark.asyncio
async def test_logistics_agent_car_estimates_currency_and_deeplink_ag053_ag055():
    """Verify car estimates output requested currency and include pickup/dropoff/dates in deeplink."""
    agent = LogisticsAgent()

    constraints = TravelConstraints(
        origin="LHR",
        destination_region="France",
        duration_days=5,
        cities=["Paris", "Lyon"],
        budget_total=2500.0,
        currency="EUR",
        is_road_trip=True
    )

    cars = agent._generate_car_estimates(constraints)
    assert len(cars) >= 3

    for car in cars:
        assert car.currency == "EUR"
        assert car.is_estimate is True
        assert car.deeplink is not None
        assert "https://www.skyscanner.net/carhire" in car.deeplink
        assert "pickup=" in car.deeplink
        assert "dropoff=" in car.deeplink
