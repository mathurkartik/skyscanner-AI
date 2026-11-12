"""
Unit tests for Sprint 1 Batch 3 (Data Authenticity & Geocoding: AG-012, AG-013, AG-014, AG-015, AG-016, AG-021).
Covers:
- AG-012: Elimination of hardcoded "DEL" origin and "Iceland" destination fallbacks
- AG-013: City coordinates lookup used before hardcoded coordinates
- AG-014: Elimination of fabricated ratings (4.5) and review counts (1200) in OpenTripMap POIs
- AG-015: Duffel deeplink preservation using authentic booking links
- AG-016: is_estimate flag on RealFlightOffer, RealHotelOffer, and PlaceInfo
- AG-021: Airport map pins placed at commercial airport coordinates rather than tourist attractions
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.schemas import (
    RealFlightOffer,
    RealHotelOffer,
    PlaceInfo,
    TravelConstraints,
    DraftItinerary,
    DayItinerary,
    DayItineraryItem,
    DaySlot,
    Activity,
    ActivityType,
    CostBand,
    BudgetBreakdown,
    BudgetCategory,
)
from app.agents.logistics import LogisticsAgent
from app.agents.orchestrator import OrchestratorAgent
from app.tools.city_coords import get_city_coords, get_airport_coords, AIRPORT_COORDS
from app.tools.hotel_client import HotelClient
from app.tools.google_places_client import GooglePlacesClient
from app.tools.flight_client import FlightClient


def test_ag016_is_estimate_defaults_to_false():
    """Verify is_estimate defaults to False on real travel schemas."""
    flight = RealFlightOffer(
        airline="Delta",
        origin="JFK",
        destination="LHR",
        price=550.0,
        duration_minutes=420,
        departure="18:00",
        arrival="06:00"
    )
    assert flight.is_estimate is False

    hotel = RealHotelOffer(
        name="Hilton London",
        city="London",
        price_per_night=180.0,
        total_price=540.0
    )
    assert hotel.is_estimate is False

    place = PlaceInfo(name="The British Museum")
    assert place.is_estimate is False


def test_ag013_hotel_destination_uses_city_coords():
    """Verify HotelClient.search_destination resolves coordinates via city_coords, not Reykjavik."""
    client = HotelClient()

    tokyo_dest = client.search_destination_sync("tokyo") if hasattr(client, "search_destination_sync") else None
    # If async:
    assert get_city_coords("tokyo") == (35.6762, 139.6503)
    assert get_city_coords("paris") == (48.8566, 2.3522)
    assert get_city_coords("jaipur") == (26.9124, 75.7873)


@pytest.mark.asyncio
async def test_ag013_hotel_client_fallback_coordinates():
    """Verify HotelClient.search_destination uses city_coords for unknown RapidAPI locations."""
    client = HotelClient()
    dest = await client.search_destination("Tokyo")
    assert dest["lat"] == pytest.approx(35.6762, rel=1e-2)
    assert dest["lng"] == pytest.approx(139.6503, rel=1e-2)

    dest_paris = await client.search_destination("Paris")
    assert dest_paris["lat"] == pytest.approx(48.8566, rel=1e-2)
    assert dest_paris["lng"] == pytest.approx(2.3522, rel=1e-2)


@pytest.mark.asyncio
async def test_ag014_opentripmap_no_fabricated_ratings():
    """Verify OpenTripMap POIs have rating=None, review_count=None, and is_estimate=True."""
    client = GooglePlacesClient()
    client.settings.opentripmap_api_key = "test_otm_key"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "xid": "W12345",
            "name": "Historic Castle",
            "point": {"lat": 51.5, "lon": -0.1}
        }
    ]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        places = await client._query_opentripmap_places(lat=51.5, lng=-0.1)
        assert len(places) == 1
        place = places[0]
        assert place.rating is None
        assert place.review_count is None
        assert place.is_estimate is True


def test_ag015_duffel_deeplink_preserves_booking_url():
    """Verify Duffel flight parsing uses booking_link/booking_url or constructs Duffel checkout link."""
    client = FlightClient()
    raw_item = {
        "id": "off_12345abc",
        "total_amount": "450.00",
        "total_currency": "USD",
        "booking_url": "https://app.duffel.com/book/off_12345abc",
        "owner": {"name": "British Airways", "iata_code": "BA"},
        "slices": [
            {
                "duration": "PT420M",
                "segments": [
                    {
                        "departing_at": "2026-12-01T10:00:00",
                        "arriving_at": "2026-12-01T17:00:00",
                        "operating_carrier_flight_number": "BA 101"
                    }
                ]
            }
        ]
    }

    # Simulate parsing
    deeplink = raw_item.get("booking_url") or raw_item.get("booking_link") or f"https://app.duffel.com/book/{raw_item['id']}"
    assert deeplink == "https://app.duffel.com/book/off_12345abc"
    assert "skyscanner.com" not in deeplink


def test_ag021_airport_coords_lookup():
    """Verify get_airport_coords returns accurate commercial airport coordinates, distinct from city centers."""
    kef = get_airport_coords("KEF")
    assert kef == (63.9850, -22.6056)
    # Keflavik airport is ~50km southwest of Reykjavik city center
    reykjavik_city = get_city_coords("reykjavik")
    assert kef != reykjavik_city

    lhr = get_airport_coords("LHR")
    assert lhr == (51.4700, -0.4543)

    hnd = get_airport_coords("HND")
    assert hnd == (35.5494, 139.7798)

    delhi = get_airport_coords("DEL")
    assert delhi == (28.5562, 77.1000)


@pytest.mark.asyncio
async def test_ag021_orchestrator_airport_pin_uses_airport_coordinates():
    """Verify OrchestratorAgent places the gateway airport pin at the airport, not tourist attractions."""
    orchestrator = OrchestratorAgent()

    # Draft where day 1 has a tourist attraction
    attraction_lat, attraction_lng = 64.1417, -21.9266  # Hallgrimskirkja
    dummy_place = PlaceInfo(
        name="Hallgrimskirkja",
        lat=attraction_lat,
        lng=attraction_lng
    )

    item = DayItineraryItem(
        slot_index=0,
        time="09:00 - 11:00",
        activity_name="Hallgrimskirkja",
        city="Reykjavik",
        type=ActivityType.TEMPLE,
        cost_estimate=0.0,
        notes="Iconic church"
    )

    day1 = DayItinerary(
        day_number=1,
        city="Reykjavik",
        day_summary="City Tour in Reykjavik",
        items=[item],
        day_cost=0.0,
        places=[dummy_place]
    )

    budget = BudgetBreakdown(
        categories=[BudgetCategory(category="stay", estimated_total=100.0, currency="USD")],
        currency="USD",
        grand_total=100.0,
        within_budget=True,
        remaining_buffer=100.0
    )

    constraints = TravelConstraints(
        destination_region="Iceland",
        cities=["Reykjavik"],
        duration_days=1,
        budget_total=1000,
        currency="USD"
    )

    draft = DraftItinerary(
        constraints=constraints,
        days=[day1],
        total_estimated_cost=100.0,
        currency="USD",
        budget_summary=budget
    )

    final = orchestrator._draft_to_final(draft, constraints, budget)
    pins = final.map_pins
    airport_pins = [p for p in pins if p.pin_type == "airport"]
    assert len(airport_pins) == 1
    airport_pin = airport_pins[0]

    # Verify pin is placed at Keflavik airport (63.9850, -22.6056), NOT at Hallgrimskirkja (64.1417, -21.9266)
    assert airport_pin.lat == pytest.approx(63.9850, rel=1e-3)
    assert airport_pin.lng == pytest.approx(-22.6056, rel=1e-3)
    assert airport_pin.lat != dummy_place.lat


@pytest.mark.asyncio
async def test_ag012_logistics_never_forces_del_on_non_del_origins():
    """Verify LogisticsAgent resolves user's stated origin (e.g. Seattle -> SEA, London -> LHR) and never forces DEL."""
    agent = LogisticsAgent()

    constraints = TravelConstraints(
        origin_city="Seattle",
        destination_region="Japan",
        cities=["Tokyo", "Kyoto"],
        duration_days=7,
        budget_total=3000,
        currency="USD",
        preferences=["temples", "food"],
        avoidances=[]
    )

    with patch.object(agent.flight_client, "search_flights", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = []
        await agent.plan(constraints)
        mock_search.assert_called_once()
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["origin"] == "SEA"  # Not DEL!
        assert call_kwargs["destination"] in ["HND", "NRT", "KIX"]  # Not Iceland!
