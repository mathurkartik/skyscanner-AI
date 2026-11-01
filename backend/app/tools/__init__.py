"""
Tooling Layer - Phase 3 & Skyscanner Integration.
Capabilities: search, geo/routing, pricing, FX, live flights, live hotels.
Agents call tools through ToolRouter with logging, timeouts, caching.
"""

from .router import ToolRouter
from .flight_client import FlightClient, get_flight_client, resolve_iata
from .hotel_client import HotelClient, get_hotel_client, KNOWN_DESTINATIONS
from .google_places_client import (
    GooglePlacesClient,
    get_google_places_client,
    CURATED_PLACES,
)

__all__ = [
    "ToolRouter",
    "FlightClient",
    "get_flight_client",
    "resolve_iata",
    "HotelClient",
    "get_hotel_client",
    "KNOWN_DESTINATIONS",
    "GooglePlacesClient",
    "get_google_places_client",
    "CURATED_PLACES",
]
