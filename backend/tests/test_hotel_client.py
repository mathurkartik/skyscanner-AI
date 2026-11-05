"""
Tests for HotelClient (Phase 2).
Verifies destination resolution, RapidAPI transformation, caching, and fallback hotel search for Reykjavik, Vik, and Akureyri.
"""

import pytest
from app.tools.hotel_client import HotelClient
from app.models.schemas import RealHotelOffer


@pytest.mark.asyncio
async def test_search_destination_mapping():
    """Verify destination search resolves known cities to dest_id and coordinates."""
    client = HotelClient()
    
    # Reykjavik
    dest_reyk = await client.search_destination("Reykjavik")
    assert dest_reyk["dest_id"] is not None
    assert "Reykjavik" in dest_reyk["label"]

    # Vik
    dest_vik = await client.search_destination("Vik")
    assert dest_vik["dest_id"] is not None
    assert "Vik" in dest_vik["label"]

    # Akureyri
    dest_aku = await client.search_destination("Akureyri")
    assert dest_aku["dest_id"] is not None
    assert "Akureyri" in dest_aku["label"]

    # Tokyo
    dest_tokyo = await client.search_destination("Tokyo")
    assert dest_tokyo["dest_id"] is not None
    assert "Tokyo" in dest_tokyo["label"]


@pytest.mark.asyncio
async def test_search_destination_caching():
    """Verify 24-hour cache for destination queries."""
    client = HotelClient()
    
    res1 = await client.search_destination("Reykjavik")
    res2 = await client.search_destination("Reykjavik")
    
    assert res1 == res2


@pytest.mark.asyncio
async def test_search_hotels_reykjavik():
    """Verify exit criteria: real hotel offers for Reykjavik with prices, ratings, and images."""
    client = HotelClient()
    
    offers = await client.search_hotels(
        dest_id="-2646452",
        city_name="Reykjavik",
        arrival_date="2026-12-01",
        departure_date="2026-12-04"
    )
    
    assert len(offers) >= 3
    names = [o.name for o in offers]
    assert len(names) >= 3
    
    for offer in offers:
        assert isinstance(offer, RealHotelOffer)
        assert offer.city == "Reykjavik"
        assert offer.price_per_night > 0
        assert offer.total_price > 0
        assert offer.guest_rating > 8.0
        assert offer.image_url.startswith("https://")
        assert len(offer.amenities) > 0


@pytest.mark.asyncio
async def test_search_hotels_vik():
    """Verify exit criteria: real hotel offers for Vik with prices, ratings, and images."""
    client = HotelClient()
    
    offers = await client.search_hotels(
        dest_id="-2646892",
        city_name="Vik",
        arrival_date="2026-12-04",
        departure_date="2026-12-06"
    )
    
    assert len(offers) >= 3
    names = [o.name for o in offers]
    assert len(names) >= 3
    
    for offer in offers:
        assert isinstance(offer, RealHotelOffer)
        assert offer.city == "Vik"
        assert offer.price_per_night > 0
        assert offer.image_url.startswith("https://")


@pytest.mark.asyncio
async def test_search_hotels_akureyri():
    """Verify exit criteria: real hotel offers for Akureyri with prices, ratings, and images."""
    client = HotelClient()
    
    offers = await client.search_hotels(
        dest_id="-2641512",
        city_name="Akureyri",
        arrival_date="2026-12-06",
        departure_date="2026-12-08"
    )
    
    assert len(offers) >= 3
    names = [o.name for o in offers]
    assert len(names) >= 3
    
    for offer in offers:
        assert isinstance(offer, RealHotelOffer)
        assert offer.city == "Akureyri"
        assert offer.price_per_night > 0
        assert offer.image_url.startswith("https://")


@pytest.mark.asyncio
async def test_search_hotels_by_coords():
    """Verify search by coordinates fallback."""
    client = HotelClient()
    
    offers = await client.search_hotels_by_coords(
        lat=64.1466,
        lng=-21.9426,
        city_name="Reykjavik",
        arrival_date="2026-12-01",
        departure_date="2026-12-04"
    )
    
    assert len(offers) > 0
    assert offers[0].city == "Reykjavik"


def test_transform_booking_hotels():
    """Verify mapping of raw Booking.com RapidAPI JSON to RealHotelOffer models."""
    client = HotelClient()
    
    mock_results = [
        {
            "hotel_id": 123456,
            "hotel_name": "Test Boutique Hotel",
            "min_total_price": 450.0,
            "class": 4.0,
            "review_score": 9.2,
            "review_nr": 850,
            "address": "Laugavegur 1, Reykjavik",
            "district": "Downtown",
            "max_photo_url": "https://example.com/photo.jpg",
            "url": "https://www.booking.com/hotel/is/test.html"
        }
    ]
    
    offers = client._transform_booking_hotels(mock_results, "Reykjavik", "USD", nights=3)
    
    assert len(offers) == 1
    offer = offers[0]
    assert offer.name == "Test Boutique Hotel"
    assert offer.price_per_night == 150.0
    assert offer.total_price == 450.0
    assert offer.star_rating == 4.0
    assert offer.guest_rating == 9.2
    assert offer.review_count == 850
    assert offer.image_url == "https://example.com/photo.jpg"
    assert offer.neighborhood == "Downtown"

