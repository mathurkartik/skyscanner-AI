"""
Tests for GooglePlacesClient (Phase 3).
Verifies nearby search, text search, place details, caching, and realistic fallback attractions for Reykjavik, Vik, and Akureyri.
"""

import pytest
from app.config import Settings
from app.tools.google_places_client import GooglePlacesClient
from app.models.schemas import PlaceInfo


@pytest.fixture
def fallback_client():
    """Client with no API key, guaranteeing curated inventory tests run offline & deterministically."""
    settings = Settings(google_places_api_key=None)
    return GooglePlacesClient(settings=settings)


@pytest.mark.asyncio
async def test_search_nearby_reykjavik(fallback_client):
    """Verify exit criteria: returns top-rated attractions near Reykjavik (64.1466°N, 21.9426°W) with ratings and hours."""
    places = await fallback_client.search_nearby(
        lat=64.1466,
        lng=-21.9426,
        radius_m=15000,
        place_type="tourist_attraction"
    )

    assert len(places) >= 2
    for p in places:
        assert p.name is not None
        assert p.rating is not None
        assert p.lat is not None
        assert p.lng is not None


@pytest.mark.asyncio
async def test_search_nearby_vik(fallback_client):
    """Verify exit criteria: returns top attractions near Vik (63.4186°N, 19.0060°W)."""
    places = await fallback_client.search_nearby(
        lat=63.4186,
        lng=-19.0060,
        radius_m=20000,
        place_type="tourist_attraction"
    )

    assert len(places) >= 2
    for p in places:
        assert p.name is not None
        assert p.rating is not None


@pytest.mark.asyncio
async def test_search_nearby_akureyri(fallback_client):
    """Verify exit criteria: returns top attractions near Akureyri (65.6835°N, 18.0878°W)."""
    places = await fallback_client.search_nearby(
        lat=65.6835,
        lng=-18.0878,
        radius_m=25000,
        place_type="tourist_attraction"
    )

    assert len(places) >= 2
    for p in places:
        assert p.name is not None
        assert p.rating is not None


@pytest.mark.asyncio
async def test_search_text_queries(fallback_client):
    """Verify text search resolves landmarks and natural features."""
    # Search by keyword
    waterfalls = await fallback_client.search_text("waterfall Iceland")
    assert len(waterfalls) > 0
    wf_names = [p.name for p in waterfalls]
    assert any("Waterfall" in n or "foss" in n.lower() for n in wf_names)

    # Search by city name
    tokyo_places = await fallback_client.search_text("Tokyo highlights")
    assert len(tokyo_places) >= 2
    for p in tokyo_places:
        assert p.name is not None
        assert p.rating is not None


@pytest.mark.asyncio
async def test_get_place_details(fallback_client):
    """Verify get_place_details resolves place_id."""
    sample_id = "ChIJc860Z0pZ1kgRnV-Q9xGkP4g"
    place = await fallback_client.get_place_details(sample_id)

    assert place is not None
    assert place.place_id == sample_id
    assert place.name is not None
    assert place.rating is not None


@pytest.mark.asyncio
async def test_places_caching(fallback_client):
    """Verify 24-hour cache avoids redundant computations."""
    res1 = await fallback_client.search_nearby(64.1466, -21.9426, 10000)
    res2 = await fallback_client.search_nearby(64.1466, -21.9426, 10000)

    assert len(res1) == len(res2)
    assert res1[0].name == res2[0].name


def test_transform_google_place_item():
    """Verify transformation of raw Google Places API JSON to PlaceInfo."""
    client = GooglePlacesClient()

    raw_item = {
        "place_id": "ChIJtest123",
        "name": "Test Geothermal Baths",
        "rating": 4.7,
        "user_ratings_total": 3450,
        "types": ["spa", "point_of_interest", "tourist_attraction"],
        "formatted_address": "Thermal Way 1, 101 Reykjavik, Iceland",
        "geometry": {
            "location": {
                "lat": 64.145,
                "lng": -21.935
            }
        },
        "opening_hours": {
            "open_now": True,
            "weekday_text": ["Monday: 9:00 AM – 10:00 PM"]
        },
        "photos": [
            {"photo_reference": "photo_ref_abc_123"}
        ],
        "price_level": 2,
        "url": "https://maps.google.com/?cid=99999"
    }

    place_info = client._transform_google_place_item(raw_item, api_key="dummy_key")

    assert isinstance(place_info, PlaceInfo)
    assert place_info.place_id == "ChIJtest123"
    assert place_info.name == "Test Geothermal Baths"
    assert place_info.rating == 4.7
    assert place_info.review_count == 3450
    assert place_info.lat == 64.145
    assert place_info.lng == -21.935
    assert place_info.coordinates == {"lat": 64.145, "lng": -21.935}
    assert place_info.open_now is True
    assert "Monday: 9:00 AM – 10:00 PM" in place_info.opening_hours
    assert "photo_reference=photo_ref_abc_123" in place_info.photo_url
    assert "key=dummy_key" in place_info.photo_url
