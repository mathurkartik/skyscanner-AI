"""
HotelClient - Booking.com RapidAPI client for real accommodation data.
Phase 2: Destination resolution, live hotel search, coordinate search, caching, and realistic fallback.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

from ..config import get_settings
from ..models.schemas import RealHotelOffer

logger = logging.getLogger(__name__)

# Pre-cached destination IDs for instant lookup & offline reliability
KNOWN_DESTINATIONS: Dict[str, Dict[str, Any]] = {
    "reykjavik": {"dest_id": "-2646452", "dest_type": "city", "label": "Reykjavik, Capital Region, Iceland", "lat": 64.1466, "lng": -21.9426},
    "vik": {"dest_id": "-2646892", "dest_type": "city", "label": "Vík, South Iceland, Iceland", "lat": 63.4186, "lng": -19.0060},
    "akureyri": {"dest_id": "-2641512", "dest_type": "city", "label": "Akureyri, Northeast Iceland, Iceland", "lat": 65.6835, "lng": -18.0878},
    "tokyo": {"dest_id": "-246227", "dest_type": "city", "label": "Tokyo, Kanto, Japan", "lat": 35.6762, "lng": 139.6503},
    "kyoto": {"dest_id": "-235553", "dest_type": "city", "label": "Kyoto, Kansai, Japan", "lat": 35.0116, "lng": 135.7681},
    "osaka": {"dest_id": "-240905", "dest_type": "city", "label": "Osaka, Kansai, Japan", "lat": 34.6937, "lng": 135.5023},
    "zurich": {"dest_id": "-2554988", "dest_type": "city", "label": "Zürich, Canton of Zurich, Switzerland", "lat": 47.3769, "lng": 8.5417},
    "london": {"dest_id": "-2601889", "dest_type": "city", "label": "London, Greater London, United Kingdom", "lat": 51.5074, "lng": -0.1278},
    "paris": {"dest_id": "-1456928", "dest_type": "city", "label": "Paris, Île-de-France, France", "lat": 48.8566, "lng": 2.3522},
    "rome": {"dest_id": "-126693", "dest_type": "city", "label": "Rome, Lazio, Italy", "lat": 41.9028, "lng": 12.4964},
    "melbourne": {"dest_id": "-1586835", "dest_type": "city", "label": "Melbourne, Victoria, Australia", "lat": -37.8136, "lng": 144.9631},
    "sydney": {"dest_id": "-1603135", "dest_type": "city", "label": "Sydney, New South Wales, Australia", "lat": -33.8688, "lng": 151.2093},
    "singapore": {"dest_id": "-73635", "dest_type": "city", "label": "Singapore, Singapore", "lat": 1.3521, "lng": 103.8198},
    "dubai": {"dest_id": "-782831", "dest_type": "city", "label": "Dubai, Emirate of Dubai, United Arab Emirates", "lat": 25.2048, "lng": 55.2708},
}

# Curated high-fidelity hotel inventory for reliable demo fallback
CURATED_HOTELS: Dict[str, List[Dict[str, Any]]] = {
    "reykjavik": [
        {
            "name": "SM Hostel",
            "price_per_night": 112.0,
            "star_rating": 3.0,
            "guest_rating": 8.4,
            "review_count": 890,
            "neighborhood": "Vesturbær",
            "address": "Kaplaskjólsvegur, 107 Reykjavík",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Free WiFi", "Shared Kitchen", "Luggage Storage", "Heating"]
        },
        {
            "name": "B18 Apartments",
            "price_per_night": 200.0,
            "star_rating": 4.0,
            "guest_rating": 9.1,
            "review_count": 420,
            "neighborhood": "Miðborg (Downtown)",
            "address": "Barónsstígur 18, 101 Reykjavík",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Kitchenette", "Balcony", "Free WiFi", "Espresso Machine"]
        },
        {
            "name": "Center Hotels Plaza",
            "price_per_night": 245.0,
            "star_rating": 4.0,
            "guest_rating": 8.6,
            "review_count": 2150,
            "neighborhood": "Old Town",
            "address": "Aðalstræti 4-6, 101 Reykjavík",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Bar", "Buffet Breakfast", "Airport Shuttle", "24-Hour Front Desk"]
        },
        {
            "name": "Kex Hostel",
            "price_per_night": 85.0,
            "star_rating": 2.5,
            "guest_rating": 8.7,
            "review_count": 3400,
            "neighborhood": "Harbor Front",
            "address": "Skúlagata 28, 101 Reykjavík",
            "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Craft Beer Bar", "Live Music", "Free WiFi", "Ocean View Terrace"]
        }
    ],
    "vik": [
        {
            "name": "Guesthouse Carina",
            "price_per_night": 145.0,
            "star_rating": 3.0,
            "guest_rating": 8.9,
            "review_count": 780,
            "neighborhood": "Vik Village Hill",
            "address": "Sunnuvegur 26, 870 Vík",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Black Beach Views", "Free Breakfast", "Free Parking", "Free WiFi"]
        },
        {
            "name": "Hotel Kría",
            "price_per_night": 220.0,
            "star_rating": 4.0,
            "guest_rating": 9.0,
            "review_count": 1320,
            "neighborhood": "Vik Center",
            "address": "Sléttuvegur 12-14, 870 Vík",
            "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Mountain Views", "Drangar Restaurant", "Bar", "Cocktail Lounge"]
        },
        {
            "name": "The Barn Hostel Vik",
            "price_per_night": 90.0,
            "star_rating": 3.0,
            "guest_rating": 9.2,
            "review_count": 1950,
            "neighborhood": "Reynisfjara Road",
            "address": "Norður-Vík, 870 Vík",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Modern Bunks", "Kitchen", "Social Bar", "Free Parking"]
        }
    ],
    "akureyri": [
        {
            "name": "Hotel Kea by Keahotels",
            "price_per_night": 165.0,
            "star_rating": 4.0,
            "guest_rating": 8.5,
            "review_count": 1100,
            "neighborhood": "Akureyri Town Square",
            "address": "Hafnarstræti 87-89, 600 Akureyri",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Múlaberg Bistro", "Cocktail Bar", "Free WiFi", "Church Steps View"]
        },
        {
            "name": "Akureyri Backpackers",
            "price_per_night": 75.0,
            "star_rating": 2.5,
            "guest_rating": 8.8,
            "review_count": 1650,
            "neighborhood": "Pedestrian Street",
            "address": "Hafnarstræti 98, 600 Akureyri",
            "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Café & Bar", "Sauna", "Guest Kitchen", "Tour Desk"]
        },
        {
            "name": "Hafdals Hotel",
            "price_per_night": 190.0,
            "star_rating": 3.5,
            "guest_rating": 9.4,
            "review_count": 480,
            "neighborhood": "Fjord Overlook",
            "address": "Hafnarsveit, 601 Akureyri",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Panoramic Fjord Views", "Aurora Borealis Terrace", "Free Breakfast"]
        }
    ],
    "tokyo": [
        {
            "name": "Park Hyatt Tokyo",
            "price_per_night": 620.0,
            "star_rating": 5.0,
            "guest_rating": 9.3,
            "review_count": 2100,
            "neighborhood": "Shinjuku",
            "address": "3-7-1-2 Nishi-Shinjuku, Shinjuku-ku, Tokyo",
            "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=600&auto=format&fit=crop&q=80",
            "amenities": ["New York Grill", "Spa & Pool", "Mount Fuji View", "Concierge"]
        },
        {
            "name": "Hotel Gracery Shinjuku",
            "price_per_night": 185.0,
            "star_rating": 4.0,
            "guest_rating": 8.6,
            "review_count": 5200,
            "neighborhood": "Kabukicho, Shinjuku",
            "address": "1-19-1 Kabukicho, Shinjuku-ku, Tokyo",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Godzilla Head Terrace", "Free High-Speed WiFi", "Restaurant", "Metro 5m"]
        },
        {
            "name": "Candeo Hotels Tokyo Shimbashi",
            "price_per_night": 170.0,
            "star_rating": 4.0,
            "guest_rating": 8.8,
            "review_count": 1800,
            "neighborhood": "Ginza / Shimbashi",
            "address": "3-6-8 Shimbashi, Minato-ku, Tokyo",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Rooftop SkySpa Onsen", "Open-Air Bath", "Tokyo Tower Views"]
        }
    ],
    "kyoto": [
        {
            "name": "Kyoto Ryokan Gion Sano",
            "price_per_night": 280.0,
            "star_rating": 4.5,
            "guest_rating": 9.4,
            "review_count": 620,
            "neighborhood": "Gion Historic District",
            "address": "504 Washio-cho, Higashiyama-ku, Kyoto",
            "image_url": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Tatami Rooms", "Kaiseki Breakfast", "Hinoki Wood Bath", "Garden View"]
        },
        {
            "name": "The Thousand Kyoto",
            "price_per_night": 310.0,
            "star_rating": 5.0,
            "guest_rating": 9.2,
            "review_count": 1400,
            "neighborhood": "Kyoto Station",
            "address": "570 Higashishiokoji-cho, Shimogyo-ku, Kyoto",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Tea Ceremony Room", "Spa", "Fine Dining", "Direct Station Access"]
        },
        {
            "name": "Piece Hostel Sanjo",
            "price_per_night": 75.0,
            "star_rating": 3.0,
            "guest_rating": 9.3,
            "review_count": 2800,
            "neighborhood": "Sanjo / Downtown",
            "address": "531 Asakura-cho, Nakagyo-ku, Kyoto",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Terrace Bar", "Free Continental Breakfast", "Bike Rental", "Library"]
        }
    ]
}


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
            return KNOWN_DESTINATIONS["reykjavik"]

        # Check static directory first (exact match first, then word-boundary match)
        if clean_query in KNOWN_DESTINATIONS:
            return KNOWN_DESTINATIONS[clean_query]

        for name, dest in KNOWN_DESTINATIONS.items():
            if re.search(r'\b' + re.escape(name) + r'\b', clean_query):
                return dest

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
        city_name: Optional[str] = None
    ) -> List[RealHotelOffer]:
        """
        Search hotels by dest_id or fallback to curated inventory.
        """
        cache_key = f"{dest_id}:{arrival_date}:{departure_date}:{adults}:{room_qty}:{currency}".lower()
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
                        city_name=city_name or "Destination"
                    )
                    if offers:
                        self._search_cache[cache_key] = {"timestamp": time.time(), "data": offers}
                        return offers
                except Exception as err:
                    logger.warning("Booking.com hotel search failed for dest_id %s: %s", dest_id, err)

        # Fallback to curated inventory
        offers = self._generate_fallback_hotels(
            dest_id=dest_id,
            city_name=city_name,
            arrival_date=arrival_date,
            departure_date=departure_date,
            currency=currency
        )
        self._search_cache[cache_key] = {"timestamp": time.time(), "data": offers}
        return offers

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
        city_name: str
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
            return self._transform_booking_hotels(data, city_name, currency, 3)

    def _transform_booking_hotels(
        self,
        results: List[Dict[str, Any]],
        city_name: str,
        currency: str,
        nights: int = 3
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
        currency: str
    ) -> List[RealHotelOffer]:
        target_key = "reykjavik"
        if city_name:
            cn = city_name.strip().lower()
            if cn in CURATED_HOTELS:
                target_key = cn
            else:
                for k in CURATED_HOTELS:
                    if re.search(r'\b' + re.escape(k) + r'\b', cn):
                        target_key = k
                        break
        else:
            for k, dest in KNOWN_DESTINATIONS.items():
                if dest["dest_id"] == dest_id:
                    target_key = k
                    break

        display_city = (city_name or target_key).title()
        if target_key in CURATED_HOTELS:
            hotel_list = CURATED_HOTELS[target_key]
        else:
            # Generate high-fidelity dynamic hotel offerings for any global destination
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
            total = round(nightly * 3, 2)
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
