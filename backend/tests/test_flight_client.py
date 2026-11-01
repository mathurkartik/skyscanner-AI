"""
Tests for FlightClient (Phase 1).
Verifies IATA resolution, RapidAPI transformation, caching, and realistic fallback.
"""

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock

from app.tools.flight_client import FlightClient, resolve_iata
from app.models.schemas import RealFlightOffer


def test_resolve_iata_mapping():
    """Verify city name to IATA airport code resolution."""
    assert resolve_iata("Nagpur") == "NAG"
    assert resolve_iata("nagpur") == "NAG"
    assert resolve_iata("Reykjavik") == "KEF"
    assert resolve_iata("Iceland") == "KEF"
    assert resolve_iata("Tokyo") == "HND"
    assert resolve_iata("Melbourne") == "MEL"
    assert resolve_iata("Zurich") == "ZRH"
    assert resolve_iata("London") == "LHR"
    assert resolve_iata("Paris") == "CDG"
    assert resolve_iata("Delhi") == "DEL"
    assert resolve_iata("Mumbai") == "BOM"
    
    # Existing 3-letter IATA codes
    assert resolve_iata("KEF") == "KEF"
    assert resolve_iata("NAG") == "NAG"
    assert resolve_iata("MEL") == "MEL"
    assert resolve_iata("HND") == "HND"


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
        assert offer.stops >= 1
        assert len(offer.airline) > 0
        assert offer.departure is not None
        assert offer.arrival is not None
        assert offer.return_departure is not None
        assert "skyscanner.com" in offer.deeplink


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

