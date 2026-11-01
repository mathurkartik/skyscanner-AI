"""
Tests for API Plan and Booking endpoints (Phase 11 & Phase 12).
Verifies demo blueprints, booking integration, and 3-pillar validation.
"""

import pytest
import pytest_asyncio
import httpx
from app.main import app


@pytest_asyncio.fixture
async def async_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_plan_endpoint_iceland_stub_blueprint(async_client):
    payload = {
        "request": "Plan an 11-day road trip to Iceland with a budget of ₹350000. Ring Road adventure.",
        "stub_mode": True
    }
    response = await async_client.post("/api/plan", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["used_stub_mode"] is True
    itinerary = data["final_itinerary"]
    assert len(itinerary["days"]) == 11
    assert "Iceland" in itinerary["constraints"]["destination_region"]
    assert itinerary["constraints"]["is_road_trip"] is True

    # Real flight offers
    assert len(itinerary["flight_options"]) >= 1
    flight = itinerary["flight_options"][0]
    assert flight["origin"] == "DEL"
    assert flight["destination"] == "KEF"
    assert "skyscanner.net" in flight["deeplink"]

    # Real hotel offers on day 1
    day1 = itinerary["days"][0]
    assert len(day1["hotel_options"]) >= 1
    assert "Kría" in day1["hotel_options"][0]["name"] or "Vik" in day1["hotel_options"][0]["city"]
    assert "booking.com" in day1["hotel_options"][0]["deeplink"]

    # Car estimate
    assert len(itinerary["car_estimates"]) >= 1
    car = itinerary["car_estimates"][0]
    assert "4WD" in car["vehicle_name"] or "Vitara" in car["vehicle_name"]
    assert "carhire" in car["deeplink"]

    # Verified places on day items
    all_places = [p for d in itinerary["days"] for p in d.get("places", [])]
    assert len(all_places) >= 5
    place_names = [p["name"] for p in all_places]
    assert any("Seljalandsfoss" in name for name in place_names)
    assert any("Skógafoss" in name for name in place_names)

    # Map pins
    assert len(itinerary["map_pins"]) >= 5
    pins = itinerary["map_pins"]
    assert any(p["pin_type"] == "airport" for p in pins)
    assert any(p["pin_type"] == "overnight" for p in pins)

    # Cost saving tips
    assert len(itinerary["cost_saving_tips_v2"]) >= 2

    # Budget rollup validation
    rollup = itinerary["budget_rollup"]
    assert rollup["within_budget"] is True
    calculated = sum(c["estimated_total"] for c in rollup["categories"])
    assert abs(calculated - rollup["grand_total"]) < 0.01


@pytest.mark.asyncio
async def test_plan_endpoint_japan_stub_blueprint(async_client):
    payload = {
        "request": "7-day trip to Japan visiting Tokyo and Kyoto on a $3000 budget",
        "stub_mode": True
    }
    response = await async_client.post("/api/plan", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    itinerary = data["final_itinerary"]
    assert len(itinerary["days"]) == 7
    assert "Japan" in itinerary["constraints"]["destination_region"]
    assert "Tokyo" in itinerary["constraints"]["cities"]

    # Flight offer to Haneda
    flight = itinerary["flight_options"][0]
    assert flight["destination"] == "HND"

    # Places
    all_places = [p for d in itinerary["days"] for p in d.get("places", [])]
    place_names = [p["name"] for p in all_places]
    assert any("Senso-ji" in name or "Inari" in name for name in place_names)

    # Budget rollup
    rollup = itinerary["budget_rollup"]
    calculated = sum(c["estimated_total"] for c in rollup["categories"])
    assert abs(calculated - rollup["grand_total"]) < 0.01


@pytest.mark.asyncio
async def test_plan_endpoint_swiss_stub_blueprint(async_client):
    payload = {
        "request": "7-day scenic rail journey in Switzerland Alps with €3500 budget",
        "stub_mode": True
    }
    response = await async_client.post("/api/plan", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    itinerary = data["final_itinerary"]
    assert len(itinerary["days"]) == 7
    assert "Swiss" in itinerary["constraints"]["destination_region"]

    # Flight offer to Zurich
    flight = itinerary["flight_options"][0]
    assert flight["destination"] == "ZRH"

    # Places
    all_places = [p for d in itinerary["days"] for p in d.get("places", [])]
    place_names = [p["name"] for p in all_places]
    assert any("Jungfraujoch" in name or "Matterhorn" in name for name in place_names)


@pytest.mark.asyncio
async def test_plan_endpoint_strict_missing_constraints_validation(async_client):
    # Missing duration and budget
    payload = {
        "request": "I want to visit Paris",
        "stub_mode": True
    }
    response = await async_client.post("/api/plan", json=payload)
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "missing_constraints"
    assert "duration" in detail["missing_fields"]
    assert "budget" in detail["missing_fields"]


@pytest.mark.asyncio
async def test_booking_endpoint(async_client):
    payload = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "comment": "Excited for this trip!",
        "itinerary": {
            "final_itinerary": {},
            "constraints": {
                "destination_region": "Iceland",
                "duration_days": 11,
                "budget_total": 350000,
                "currency": "INR"
            }
        }
    }
    response = await async_client.post("/api/book", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
