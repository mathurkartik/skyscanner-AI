"""
Tests for FlightClient (Phase 1).
Verifies IATA resolution, RapidAPI transformation, caching, and realistic fallback.
"""

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock

from app.tools.flight_client import FlightClient, resolve_iata, resolve_iata_sync
from app.models.schemas import RealFlightOffer


@pytest.mark.asyncio
async def test_resolve_iata_mapping():
    """Verify city name to IATA airport code resolution dynamically via LLM and cache."""
    # Direct 3-letter IATA codes
    assert await resolve_iata("KEF") == "KEF"
    assert await resolve_iata("NAG") == "NAG"
    assert await resolve_iata("MEL") == "MEL"
    assert await resolve_iata("HND") == "HND"
    assert await resolve_iata("kef") == "KEF"

    # Dynamic LLM resolution for city names
    assert await resolve_iata("Nagpur") == "NAG"
    assert await resolve_iata("Reykjavik") == "KEF"
    assert await resolve_iata("Iceland") == "KEF"
    assert await resolve_iata("Delhi") == "DEL"
    assert await resolve_iata("Mumbai") == "BOM"
    assert await resolve_iata("Tokyo") in ["HND", "NRT"]
    assert await resolve_iata("Melbourne") == "MEL"
    assert await resolve_iata("Zurich") == "ZRH"
    assert await resolve_iata("London") in ["LHR", "LGW"]
    assert await resolve_iata("Paris") in ["CDG", "ORY"]

    # Verify sync accessor
    assert resolve_iata_sync("KEF") == "KEF"
    assert resolve_iata_sync("NAG") == "NAG"
    # Cached items work synchronously
    assert resolve_iata_sync("Nagpur") == "NAG"


@pytest.mark.asyncio
async def test_search_flights_fallback():
    """Verify search_flights returns valid RealFlightOffer items with realistic hubs."""
    client = FlightClient()
    
    offers = await client.search_flights(
        origin="Nagpur",
        destination="Reykjavik",
        departure_date="2026-12-01",
        return_date="2026-12-11",
        cabin_class="economy",
        adults=1
    )
    
    assert len(offers) > 0
    for offer in offers:
        assert isinstance(offer, RealFlightOffer)
        assert offer.origin == "NAG"
        assert offer.destination == "KEF"
        assert offer.price > 0
        assert offer.duration_minutes > 0
        assert offer.stops >= 0
        assert len(offer.airline) > 0
        assert offer.departure is not None
        assert offer.arrival is not None
        assert offer.return_departure is not None
        assert "skyscanner.com" in offer.deeplink or "duffel.com" in offer.deeplink


@pytest.mark.asyncio
async def test_search_flights_caching():
    """Verify that repeated searches within TTL hit in-memory cache."""
    client = FlightClient()
    
    offers1 = await client.search_flights(
        origin="NAG",
        destination="MEL",
        departure_date="2026-12-01",
        return_date="2026-12-15"
    )
    
    offers2 = await client.search_flights(
        origin="NAG",
        destination="MEL",
        departure_date="2026-12-01",
        return_date="2026-12-15"
    )
    
    # The exact same list object is returned from cache
    assert offers1 == offers2


@pytest.mark.asyncio
async def test_transform_rapidapi_response():
    """Verify mapping of Skyscanner RapidAPI JSON payload to RealFlightOffer models."""
    client = FlightClient()
    
    mock_payload = {
        "itineraries": {
            "results": [
                {
                    "legs": [
                        {
                            "id": "leg-out-1",
                            "departure": "2026-12-01T07:15:00",
                            "arrival": "2026-12-01T19:40:00",
                            "durationInMinutes": 745,
                            "stopCount": 1,
                            "carriers": {
                                "marketing": [
                                    {"id": "6E", "name": "IndiGo", "logoUrl": "https://images.kiwi.com/airlines/64/6E.png"}
                                ]
                            },
                            "segments": [
                                {"destination": {"displayCode": "DEL"}},
                                {"destination": {"displayCode": "KEF"}}
                            ]
                        },
                        {
                            "id": "leg-in-1",
                            "departure": "2026-12-11T10:15:00",
                            "arrival": "2026-12-12T06:30:00",
                            "durationInMinutes": 735,
                            "stopCount": 1,
                            "carriers": {
                                "marketing": [
                                    {"id": "FI", "name": "Icelandair", "logoUrl": "https://images.kiwi.com/airlines/64/FI.png"}
                                ]
                            }
                        }
                    ],
                    "pricingOptions": [
                        {
                            "price": {"amount": 830.0},
                            "items": [{"url": "https://www.skyscanner.com/transport/flights/nag/kef"}]
                        }
                    ]
                }
            ]
        }
    }
    
    offers = client._transform_rapidapi_response(mock_payload, "NAG", "KEF", "USD", "economy")
    
    assert len(offers) == 1
    offer = offers[0]
    assert offer.airline == "IndiGo"
    assert offer.airline_code == "6E"
    assert offer.origin == "NAG"
    assert offer.destination == "KEF"
    assert offer.price == 830.0
    assert offer.duration_minutes == 745
    assert offer.stops == 1
    assert offer.layover_airports == ["DEL"]
    assert offer.departure == "07:15"
    assert offer.arrival == "19:40"
    assert offer.return_departure == "10:15"
    assert offer.return_arrival == "06:30"


@pytest.mark.asyncio
async def test_duffel_api_offer_parsing():
    """Verify parsing of Duffel API v2 response into RealFlightOffer models."""
    client = FlightClient()

    mock_duffel_resp = {
        "data": {
            "offers": [
                {
                    "id": "off_001",
                    "total_amount": "245.50",
                    "total_currency": "USD",
                    "owner": {
                        "name": "British Airways",
                        "iata_code": "BA",
                        "logo_symbol_url": "https://assets.duffel.com/ba.svg"
                    },
                    "slices": [
                        {
                            "duration": "PT7H45M",
                            "segments": [
                                {
                                    "operating_carrier_flight_number": "178",
                                    "departing_at": "2026-12-01T08:30:00",
                                    "arriving_at": "2026-12-01T16:15:00",
                                    "origin": {"iata_code": "LHR"}
                                }
                            ]
                        },
                        {
                            "duration": "PT7H15M",
                            "segments": [
                                {
                                    "departing_at": "2026-12-10T19:00:00",
                                    "arriving_at": "2026-12-11T07:15:00",
                                    "origin": {"iata_code": "JFK"}
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_duffel_resp

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        offers = await client._query_duffel_api(
            orig_iata="LHR",
            dest_iata="JFK",
            departure_date="2026-12-01",
            return_date="2026-12-10",
            cabin_class="economy",
            adults=1,
            currency="USD"
        )

        assert len(offers) == 1
        offer = offers[0]
        assert offer.airline == "British Airways"
        assert offer.airline_code == "BA"
        assert offer.flight_number == "178"
        assert offer.price == 245.50
        assert offer.duration_minutes == 465  # 7 * 60 + 45
        assert offer.stops == 0
        assert offer.departure == "08:30"
        assert offer.arrival == "16:15"
        assert offer.return_departure == "19:00"
        assert offer.return_arrival == "07:15"
        assert offer.return_duration_minutes == 435  # 7 * 60 + 15
        assert offer.return_stops == 0


