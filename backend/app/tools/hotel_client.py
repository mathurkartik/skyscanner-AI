"""
HotelClient - Booking.com RapidAPI client for real accommodation data.
Phase 2: Destination resolution, live hotel search, coordinate search, caching, and realistic fallback.
"""

import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

from ..config import get_settings
from ..models.schemas import RealHotelOffer
from ..llm.llm_utils import validate_llm_json

logger = logging.getLogger(__name__)

class HotelClient:
    """
    Client for Booking.com RapidAPI hotel searches with destination resolution,
    24h destination cache, 1h search cache, and curated fallback inventory.
    """

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self._dest_cache: Dict[str, Dict[str, Any]] = {}
        self._search_cache: Dict[str, Dict[str, Any]] = {}
        self.dest_cache_ttl_seconds: int = 86400  # 24 hours
        self.search_cache_ttl_seconds: int = 3600  # 1 hour

    async def search_destination(self, query: str) -> Dict[str, Any]:
        """
        Resolve city or location name to Booking.com dest_id and dest_type.
        """
        clean_query = query.strip().lower()
        if not clean_query:
            clean_query = "destination"

        # Check in-memory 24h cache
        cached = self._dest_cache.get(clean_query)
        if cached:
            age = time.time() - cached.get("timestamp", 0)
            if age < self.dest_cache_ttl_seconds:
                return cached["data"]

        # If RapidAPI key configured and explicitly enabled, query booking-com15.p.rapidapi.com
        if getattr(self.settings, "enable_rapidapi", False):
            rapidapi_key = self.settings.rapidapi_key or ""
            if rapidapi_key and rapidapi_key.strip():
                try:
                    headers = {
                        "x-rapidapi-key": rapidapi_key.strip(),
                        "x-rapidapi-host": "booking-com15.p.rapidapi.com"
                    }
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.get(
                            "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination",
                            params={"query": query},
                            headers=headers
                        )
                        if resp.status_code == 200:
                            data = resp.json().get("data", [])
                            if data and len(data) > 0:
                                first = data[0]
                                result = {
                                    "dest_id": str(first.get("dest_id", "-2646452")),
                                    "dest_type": str(first.get("dest_type", "city")),
                                    "label": first.get("label", query),
                                    "lat": float(first.get("latitude", 64.1466)),
                                    "lng": float(first.get("longitude", -21.9426))
                                }
                                self._dest_cache[clean_query] = {"timestamp": time.time(), "data": result}
                                return result
                except Exception as err:
                    logger.warning("Destination search failed for '%s': %s", query, err)

        # Default fallback
        fallback = {
            "dest_id": f"-{abs(hash(clean_query)) % 10000000}",
            "dest_type": "city",
            "label": query.title(),
            "lat": 64.1466,
            "lng": -21.9426
        }
        self._dest_cache[clean_query] = {"timestamp": time.time(), "data": fallback}
        return fallback

    async def search_hotels(
        self,
        dest_id: str,
        dest_type: str = "city",
        arrival_date: str = "2026-12-01",
        departure_date: str = "2026-12-04",
        adults: int = 1,
        room_qty: int = 1,
        currency: str = "USD",
        city_name: Optional[str] = None,
        budget_tier: str = "moderate",
        num_nights: Optional[int] = None
    ) -> List[RealHotelOffer]:
        """
        Search hotels by dest_id or fallback to curated inventory.
        AG-002: Scaled dynamically to actual stay duration (num_nights).
        """
        # Determine actual stay nights from dates if not explicitly provided
        nights_count = num_nights
        if nights_count is None or nights_count <= 0:
            try:
                from datetime import datetime
                d_arr = datetime.strptime(arrival_date, "%Y-%m-%d")
                d_dep = datetime.strptime(departure_date, "%Y-%m-%d")
                nights_count = max(1, (d_dep - d_arr).days)
            except Exception:
                nights_count = 1

        cache_key = f"{dest_id}:{arrival_date}:{departure_date}:{adults}:{room_qty}:{currency}:{budget_tier}:{nights_count}".lower()
        cached = self._search_cache.get(cache_key)
        if cached:
            age = time.time() - cached.get("timestamp", 0)
            if age < self.search_cache_ttl_seconds:
                return cached["data"]

        if getattr(self.settings, "enable_rapidapi", False):
            rapidapi_key = self.settings.rapidapi_key or ""
            if rapidapi_key and rapidapi_key.strip():
                try:
                    offers = await self._query_booking_api(
                        dest_id=dest_id,
                        dest_type=dest_type,
                        arrival_date=arrival_date,
                        departure_date=departure_date,
                        adults=adults,
                        room_qty=room_qty,
                        currency=currency,
                        city_name=city_name or "Destination",
                        num_nights=nights_count
                    )
                    if offers:
                        self._search_cache[cache_key] = {"timestamp": time.time(), "data": offers}
                        return offers
                except Exception as err:
                    logger.warning("Booking.com hotel search failed for dest_id %s: %s", dest_id, err)

        # Dynamic LLM-generated hotels matching user's budget tier
        if city_name and city_name.strip():
            llm_hotels = await self._generate_llm_hotels(
                city_name=city_name.strip(),
                budget_tier=budget_tier,
                arrival_date=arrival_date,
                departure_date=departure_date,
                currency=currency,
                num_nights=nights_count
            )
            if llm_hotels:
                self._search_cache[cache_key] = {"timestamp": time.time(), "data": llm_hotels}
                return llm_hotels

        # Fallback to curated inventory matching budget tier
        offers = self._generate_fallback_hotels(
            dest_id=dest_id,
            city_name=city_name,
            arrival_date=arrival_date,
            departure_date=departure_date,
            currency=currency,
            budget_tier=budget_tier,
            num_nights=nights_count
        )
        self._search_cache[cache_key] = {"timestamp": time.time(), "data": offers}
        return offers

    async def _generate_llm_hotels(
        self,
        city_name: str,
        budget_tier: str = "moderate",
        arrival_date: str = "2026-12-01",
        departure_date: str = "2026-12-04",
        currency: str = "USD",
        num_nights: int = 1
    ) -> List[RealHotelOffer]:
        """Generate 3 real existing hotels in city_name using Groq/LLM."""
        if not city_name or len(city_name.strip()) < 2:
            return []
        try:
            from ..llm import get_llm_client
            llm = get_llm_client()
            if not llm:
                return []

            clean_city = city_name.strip().title()
            if budget_tier == "luxury":
                tier_instruction = f"Hotels MUST match the LUXURY tier (5-star hotels, luxury resorts, boutique palaces, 4.5-5.0 stars) with realistic nightly rates $350 - $800+ USD."
            elif budget_tier == "budget":
                tier_instruction = f"Hotels MUST match the BUDGET tier (hostels, 3-star boutique hotels, clean guest houses) with realistic nightly rates $35 - $80 USD."
            else:
                tier_instruction = f"Hotels MUST match the MID-RANGE tier (4-star hotels, boutique properties) with realistic nightly rates $110 - $220 USD."

            prompt = f"""Generate 3 REAL, currently operating hotels in {clean_city}.
{tier_instruction}
Return ONLY a valid JSON array of 3 objects with this exact format:
[
  {{
    "name": "Actual Real Hotel Name",
    "price_per_night": 150.0,
    "star_rating": 4.0,
    "guest_rating": 8.8,
    "review_count": 1250,
    "neighborhood": "Real Neighborhood or District",
    "address": "Real street address or district, {clean_city}",
    "amenities": ["Free WiFi", "Breakfast Included", "Air Conditioning"]
  }}
]"""
            response = await asyncio.wait_for(
                llm.chat_with_retry(
                    messages=[
                        {"role": "system", "content": "You are a hotel booking inventory data engine. Return ONLY a valid JSON array of real hotels."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=600
                ),
                timeout=25.0
            )
            text = response.strip()
            bracket = text.find("[")
            if bracket >= 0:
                text = text[bracket:]
                end_b = text.rfind("]")
                if end_b > 0:
                    text = text[:end_b + 1]
            data = json.loads(text)
            validate_llm_json(data, expected_type=list, caller_name="HotelClient._generate_llm_hotels")
            offers = []
            for idx, h in enumerate(data):
                nightly = float(h.get("price_per_night", 120.0))
                # AG-002: Calculate total price using actual stay nights, not hardcoded 3
                total = round(nightly * max(1, num_nights), 2)
                offers.append(RealHotelOffer(
                    id=f"llm-ht-{clean_city.lower().replace(' ', '-')}-{idx + 1}",
                    name=h.get("name", f"Hotel in {clean_city}"),
                    city=clean_city,
                    price_per_night=nightly,
                    total_price=total,
                    currency=currency,
                    star_rating=float(h.get("star_rating", 4.0)),
                    guest_rating=float(h.get("guest_rating", 8.5)),
                    review_count=int(h.get("review_count", 500)),
                    neighborhood=h.get("neighborhood", f"{clean_city} Center"),
                    address=h.get("address", f"{clean_city}"),
                    image_url="https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
                    deeplink=f"https://www.booking.com/searchresults.html?ss={clean_city.lower().replace(' ', '+')}",
                    amenities=h.get("amenities", ["Free WiFi", "Air Conditioning", "Breakfast"])
                ))
            if len(offers) >= 2:
                return offers
        except Exception as e:
            logger.warning("LLM hotel generation failed for %s: %s", city_name, e)
        return []

    async def search_hotels_by_coords(
        self,
        lat: float,
        lng: float,
        arrival_date: str = "2026-12-01",
        departure_date: str = "2026-12-04",
        adults: int = 1,
        currency: str = "USD",
        city_name: Optional[str] = None
    ) -> List[RealHotelOffer]:
        """
        Alternative search by geographic coordinates.
        """
        cache_key = f"{lat:.2f}:{lng:.2f}:{arrival_date}:{departure_date}:{adults}:{currency}".lower()
        cached = self._search_cache.get(cache_key)
        if cached:
            age = time.time() - cached.get("timestamp", 0)
            if age < self.search_cache_ttl_seconds:
                return cached["data"]

        if getattr(self.settings, "enable_rapidapi", False):
            rapidapi_key = self.settings.rapidapi_key or ""
            if rapidapi_key and rapidapi_key.strip():
                try:
                    headers = {
                        "x-rapidapi-key": rapidapi_key.strip(),
                        "x-rapidapi-host": "booking-com15.p.rapidapi.com"
                    }
                    params = {
                        "latitude": str(lat),
                        "longitude": str(lng),
                        "arrival_date": arrival_date,
                        "departure_date": departure_date,
                        "adults": str(adults),
                        "currency_code": currency
                    }
                    async with httpx.AsyncClient(timeout=20.0) as client:
                        resp = await client.get(
                            "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotelsByCoordinates",
                            params=params,
                            headers=headers
                        )
                        if resp.status_code == 200:
                            data = resp.json().get("data", {}).get("result", [])
                            offers = self._transform_booking_hotels(data, city_name or "Location", currency, 3)
                            if offers:
                                self._search_cache[cache_key] = {"timestamp": time.time(), "data": offers}
                                return offers
                except Exception as err:
                    logger.warning("Coordinates hotel search failed for (%f, %f): %s", lat, lng, err)

        # Fallback
        offers = self._generate_fallback_hotels(
            dest_id=f"coord-{lat:.1f}-{lng:.1f}",
            city_name=city_name or "Location",
            arrival_date=arrival_date,
            departure_date=departure_date,
            currency=currency
        )
        self._search_cache[cache_key] = {"timestamp": time.time(), "data": offers}
        return offers

    async def _query_booking_api(
        self,
        dest_id: str,
        dest_type: str,
        arrival_date: str,
        departure_date: str,
        adults: int,
        room_qty: int,
        currency: str,
        city_name: str,
        num_nights: int = 1
    ) -> List[RealHotelOffer]:
        headers = {
            "x-rapidapi-key": self.settings.rapidapi_key.strip(),
            "x-rapidapi-host": "booking-com15.p.rapidapi.com"
        }
        params = {
            "dest_id": dest_id,
            "search_type": dest_type,
            "arrival_date": arrival_date,
            "departure_date": departure_date,
            "adults": str(adults),
            "room_qty": str(room_qty),
            "currency_code": currency
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels",
                params=params,
                headers=headers
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Booking.com API status {resp.status_code}: {resp.text[:200]}")
            data = resp.json().get("data", {}).get("result", [])
            return self._transform_booking_hotels(data, city_name, currency, nights=num_nights)

    def _transform_booking_hotels(
        self,
        results: List[Dict[str, Any]],
        city_name: str,
        currency: str,
        nights: int = 1
    ) -> List[RealHotelOffer]:
        offers: List[RealHotelOffer] = []
        for idx, item in enumerate(results[:10]):
            name = item.get("hotel_name", f"Hotel {city_name}")
            price_total = float(item.get("min_total_price", 150.0 * nights))
            price_per_night = round(price_total / max(nights, 1), 2)
            star = float(item.get("class", 3.5))
            score = float(item.get("review_score", 8.5))
            reviews = int(item.get("review_nr", 500))
            address = item.get("address", f"{city_name} Center")
            neighborhood = item.get("district", city_name)
            photo = item.get("max_photo_url") or "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80"
            deeplink = item.get("url") or f"https://www.booking.com/searchresults.html?dest_id={item.get('hotel_id')}"

            offers.append(
                RealHotelOffer(
                    id=f"bk-{idx}-{item.get('hotel_id', uuid4().hex[:6])}",
                    name=name,
                    city=city_name,
                    price_per_night=price_per_night,
                    total_price=price_total,
                    currency=currency,
                    star_rating=star,
                    guest_rating=score,
                    review_count=reviews,
                    address=address,
                    neighborhood=neighborhood,
                    image_url=photo,
                    deeplink=deeplink,
                    amenities=["Free WiFi", "Private Bathroom", "Air Conditioning", "24-Hour Desk"]
                )
            )
        return offers

    def _generate_fallback_hotels(
        self,
        dest_id: str,
        city_name: Optional[str],
        arrival_date: str,
        departure_date: str,
        currency: str,
        budget_tier: str = "moderate",
        num_nights: int = 1
    ) -> List[RealHotelOffer]:
        display_city = (city_name or "Destination").title()
        target_key = display_city.lower()

        if budget_tier == "luxury":
            hotel_list = [
                {
                    "name": f"The Ritz-Carlton / Palace Resort {display_city}",
                    "price_per_night": 520.0,
                    "star_rating": 5.0,
                    "guest_rating": 9.5,
                    "review_count": 1420,
                    "neighborhood": f"{display_city} Waterfront / Golden Mile",
                    "address": f"Royal Boulevard, {display_city}",
                    "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
                    "amenities": ["Infinity Pool", "Full-Service Spa", "Fine Dining", "Butler Service", "Valet"]
                },
                {
                    "name": f"Grand {display_city} Luxury Suites & Villas",
                    "price_per_night": 410.0,
                    "star_rating": 4.8,
                    "guest_rating": 9.3,
                    "review_count": 890,
                    "neighborhood": f"Diplomatic Quarter, {display_city}",
                    "address": f"Palace Road, {display_city}",
                    "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
                    "amenities": ["Rooftop Lounge", "Spa & Sauna", "Airport Limousine", "Concierge"]
                },
                {
                    "name": f"{display_city} Heritage Luxury Boutique",
                    "price_per_night": 320.0,
                    "star_rating": 4.5,
                    "guest_rating": 9.1,
                    "review_count": 670,
                    "neighborhood": f"Historic Promenade, {display_city}",
                    "address": f"Old Harbor Drive, {display_city}",
                    "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&auto=format&fit=crop&q=80",
                    "amenities": ["Fine Dining", "Cocktail Lounge", "Chauffeured Transfers", "Free WiFi"]
                }
            ]
        elif budget_tier == "budget":
            hotel_list = [
                {
                    "name": f"{display_city} Central Hostel & Pods",
                    "price_per_night": 45.0,
                    "star_rating": 3.0,
                    "guest_rating": 8.4,
                    "review_count": 820,
                    "neighborhood": f"{display_city} Center",
                    "address": f"Station Road, {display_city}",
                    "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&auto=format&fit=crop&q=80",
                    "amenities": ["Free High-Speed WiFi", "Shared Kitchen", "Lockers", "24/7 Desk"]
                },
                {
                    "name": f"City Express Inn {display_city}",
                    "price_per_night": 65.0,
                    "star_rating": 3.5,
                    "guest_rating": 8.5,
                    "review_count": 450,
                    "neighborhood": f"Market District, {display_city}",
                    "address": f"Main Street, {display_city}",
                    "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
                    "amenities": ["Free WiFi", "Private Bathroom", "Air Conditioning", "Breakfast Included"]
                },
                {
                    "name": f"Urban Prime Suites {display_city}",
                    "price_per_night": 85.0,
                    "star_rating": 3.5,
                    "guest_rating": 8.6,
                    "review_count": 310,
                    "neighborhood": f"Downtown {display_city}",
                    "address": f"Commerce Way, {display_city}",
                    "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
                    "amenities": ["Free WiFi", "Kitchenette", "Air Conditioning", "Luggage Storage"]
                }
            ]
        else:
            hotel_list = [
                {
                    "name": f"Grand {display_city} Hotel & Suites",
                    "price_per_night": 175.0,
                    "star_rating": 4.5,
                    "guest_rating": 9.1,
                    "review_count": 640,
                    "neighborhood": f"{display_city} Center",
                    "address": f"Central Avenue, {display_city}",
                    "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
                    "amenities": ["Free WiFi", "Spa & Wellness", "Breakfast Included", "City View", "Concierge"]
                },
                {
                    "name": f"{display_city} Heritage Boutique Hotel",
                    "price_per_night": 135.0,
                    "star_rating": 4.0,
                    "guest_rating": 8.8,
                    "review_count": 480,
                    "neighborhood": f"Historic District, {display_city}",
                    "address": f"Old Town Square, {display_city}",
                    "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
                    "amenities": ["Free WiFi", "Boutique Bar", "Room Service", "Airport Shuttle"]
                },
                {
                    "name": f"Urban Prime Suites {display_city}",
                    "price_per_night": 95.0,
                    "star_rating": 3.5,
                    "guest_rating": 8.5,
                    "review_count": 310,
                    "neighborhood": f"Downtown {display_city}",
                    "address": f"Station Road, {display_city}",
                    "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&auto=format&fit=crop&q=80",
                    "amenities": ["Free High-Speed WiFi", "Kitchenette", "Air Conditioning", "24/7 Desk"]
                }
            ]

        offers: List[RealHotelOffer] = []
        for idx, h in enumerate(hotel_list):
            nightly = float(h["price_per_night"])
            total = round(nightly * max(1, num_nights), 2)
            deeplink = f"https://www.skyscanner.com/hotels/search?destination={target_key}&checkin={arrival_date}&checkout={departure_date}"

            offers.append(
                RealHotelOffer(
                    id=f"ht-{target_key}-{idx}",
                    name=h["name"],
                    city=display_city,
                    price_per_night=nightly,
                    total_price=total,
                    currency=currency,
                    star_rating=h["star_rating"],
                    guest_rating=h["guest_rating"],
                    review_count=h["review_count"],
                    neighborhood=h["neighborhood"],
                    address=h["address"],
                    image_url=h["image_url"],
                    deeplink=deeplink,
                    amenities=h["amenities"]
                )
            )

        return offers


_hotel_client_instance: Optional[HotelClient] = None


def get_hotel_client() -> HotelClient:
    """Get singleton HotelClient instance."""
    global _hotel_client_instance
    if _hotel_client_instance is None:
        _hotel_client_instance = HotelClient()
    return _hotel_client_instance
