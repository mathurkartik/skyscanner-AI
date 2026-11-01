"""
ToolRouter - Unified interface for all external capabilities.
Phase 3: Stubs with realistic static data, ready for Phase 8 real implementations.

Tools:
- search: Web search for destination research (SerpAPI/Tavily in Phase 8)
- geo_estimate: Distance and transit time estimation (Google Maps/OSRM in Phase 8)
- price_band: Price ranges for hotels/food/activities (static data + real APIs in Phase 8)
- fx_convert: Currency conversion (real FX API in Phase 8)

Architecture: Per-call timeout, trace propagation, simple in-memory cache.
"""

import asyncio
from typing import Optional, List, Dict, Any, Tuple
from functools import lru_cache
import time
from datetime import datetime


class ToolRouter:
    """
    Routes tool calls for search, geo, pricing, FX.
    
    Features:
    - Per-call timeout
    - Trace propagation
    - Simple in-memory cache
    - Logging
    
    Initially stubs; swapping to real implementations is router-only change.
    """
    
    def __init__(self, settings=None):
        self.settings = settings
        self._cache: Dict[str, Any] = {}
        self._call_log: List[Dict] = []
    
    async def search(
        self,
        query: str,
        trace_id: Optional[str] = None,
        timeout: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Web search for destination research.
        
        **Phase 3**: Returns static mock results for common queries.
        **Phase 8**: Replace with real search API (SerpAPI, Tavily, or similar).
        
        Args:
            query: Search query (e.g., "best temples in Kyoto")
            trace_id: Request trace ID for observability
            timeout: Max seconds to wait for results
            
        Returns:
            List of search results with title, snippet, url
            
        Used by: Destination Agent (Phase 4a)
        """
        cache_key = f"search:{query.lower().strip()}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Phase 3: Static mock data for common travel queries
        result = self._get_static_search_results(query)
        
        # Simulate network delay (remove in production)
        await asyncio.sleep(0.1)
        
        self._cache[cache_key] = result
        self._log_call("search", query, trace_id, result)
        return result
    
    async def geo_estimate(
        self,
        from_location: str,
        to_location: str,
        trace_id: Optional[str] = None,
        timeout: int = 5
    ) -> Dict[str, Any]:
        """
        Estimate distance and transit time between locations.
        
        **Phase 3**: Returns static estimates for common Japan routes.
        **Phase 8**: Replace with Google Maps API, OSRM, or similar.
        
        Args:
            from_location: Origin city/location
            to_location: Destination city/location
            trace_id: Request trace ID for observability
            timeout: Max seconds to wait for results
            
        Returns:
            Dict with distance_km, duration_minutes, mode, estimated_cost
            
        Used by: Logistics Agent (Phase 4b)
        """
        cache_key = f"geo:{from_location.lower()}:{to_location.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Phase 3: Static estimates for common routes
        result = self._get_static_geo_estimate(from_location, to_location)
        
        await asyncio.sleep(0.05)  # Simulate network delay
        
        self._cache[cache_key] = result
        self._log_call("geo_estimate", f"{from_location}->{to_location}", trace_id, result)
        return result
    
    async def price_band(
        self,
        category: str,  # "hotel", "food", "activity", "transport"
        city: str,
        band: str,  # "budget", "moderate", "expensive", "luxury"
        trace_id: Optional[str] = None,
        timeout: int = 3
    ) -> Dict[str, Any]:
        """
        Get price range for category in city.
        
        **Phase 3**: Returns static price data for major cities.
        **Phase 8**: Could integrate with real pricing APIs or web scraping.
        
        Args:
            category: "hotel", "food", "activity", or "transport"
            city: City name (e.g., "Tokyo", "Paris")
            band: "budget", "moderate", "expensive", "luxury"
            trace_id: Request trace ID for observability
            timeout: Max seconds to wait for results
            
        Returns:
            Dict with category, city, band, estimate (USD), notes
            
        Used by: Budget Agent (Phase 4c)
        """
        cache_key = f"price:{category.lower()}:{city.lower()}:{band.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Phase 3: Extended static price bands
        estimate, notes = self._get_static_price_band(category, city, band)
        
        await asyncio.sleep(0.02)  # Simulate network delay
        
        result = {
            "category": category,
            "city": city,
            "band": band,
            "estimate_usd": estimate,
            "notes": notes,
            "currency": "USD"
        }
        
        self._cache[cache_key] = result
        self._log_call("price_band", f"{category}/{city}/{band}", trace_id, result)
        return result
    
    async def fx_convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: str = "USD",
        trace_id: Optional[str] = None,
        timeout: int = 3
    ) -> Dict[str, Any]:
        """
        Currency conversion with rate information.
        
        **Phase 3**: Uses static exchange rates (updated periodically).
        **Phase 8**: Replace with real-time FX API (e.g., ExchangeRate-API, Fixer).
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code (e.g., "JPY", "EUR")
            to_currency: Target currency code (default "USD")
            trace_id: Request trace ID for observability
            timeout: Max seconds to wait for results
            
        Returns:
            Dict with original_amount, converted_amount, rate, from_currency, to_currency
            
        Used by: Budget Agent (Phase 4c)
        """
        cache_key = f"fx:{from_currency.upper()}:{to_currency.upper()}"
        
        # Phase 3: Static exchange rates (as of 2024)
        static_rates = {
            "USD": 1.0,
            "JPY": 0.0067,      # 1 JPY = 0.0067 USD
            "EUR": 1.09,
            "GBP": 1.27,
            "KRW": 0.00075,     # South Korean Won
            "THB": 0.028,       # Thai Baht
            "INR": 0.012,       # Indian Rupee
            "CNY": 0.14,        # Chinese Yuan
        }
        
        await asyncio.sleep(0.01)  # Simulate network delay
        
        if from_currency.upper() == to_currency.upper():
            rate = 1.0
            result_amount = amount
        else:
            # Convert to USD first, then to target
            from_rate = static_rates.get(from_currency.upper(), 1.0)
            to_rate = static_rates.get(to_currency.upper(), 1.0)
            
            if to_currency.upper() == "USD":
                rate = from_rate
                result_amount = amount * rate
            else:
                # Convert: from -> USD -> to
                usd_amount = amount * from_rate
                rate = from_rate / to_rate
                result_amount = usd_amount / to_rate
        
        result = {
            "original_amount": amount,
            "original_currency": from_currency.upper(),
            "converted_amount": round(result_amount, 2),
            "target_currency": to_currency.upper(),
            "rate": round(rate, 6),
            "rate_timestamp": "2024-01-01",  # Static for Phase 3
            "is_estimate": True  # True for Phase 3 static data
        }
        
        self._cache[cache_key] = static_rates.get(from_currency.upper(), 1.0)
        self._log_call("fx_convert", f"{amount} {from_currency}->{to_currency}", trace_id, result)
        return result
    
    def _log_call(
        self,
        tool: str,
        query: str,
        trace_id: Optional[str],
        result: Any
    ):
        """Log tool call for observability."""
        self._call_log.append({
            "timestamp": time.time(),
            "tool": tool,
            "query": query,
            "trace_id": trace_id,
            "result_summary": str(result)[:100]  # Truncated for logging
        })
    
    # =========================================================================
    # Phase 3: Static Data Methods (Replace with real APIs in Phase 8)
    # =========================================================================
    
    def _get_static_search_results(self, query: str) -> List[Dict[str, Any]]:
        """Return static mock search results for common travel queries."""
        query_lower = query.lower()
        
        # Mock results for Japan-related queries
        if "temple" in query_lower and "kyoto" in query_lower:
            return [
                {"title": "Kinkaku-ji (Golden Pavilion)", "snippet": "Iconic Zen temple covered in gold leaf", "url": "https://example.com/kinkakuji"},
                {"title": "Fushimi Inari Shrine", "snippet": "Famous for thousands of vermillion torii gates", "url": "https://example.com/fushimi"},
                {"title": "Kiyomizu-dera", "snippet": "Historic wooden temple with city views", "url": "https://example.com/kiyomizu"},
            ]
        
        if "food" in query_lower and ("tokyo" in query_lower or "japan" in query_lower):
            return [
                {"title": "Tsukiji Outer Market", "snippet": "Fresh sushi and street food", "url": "https://example.com/tsukiji"},
                {"title": "Omoide Yokocho", "snippet": "Traditional yakitori alley in Shinjuku", "url": "https://example.com/omoide"},
                {"title": "Depachika Food Halls", "snippet": "Upscale food courts in department stores", "url": "https://example.com/depachika"},
            ]
        
        # Default empty results for unknown queries
        return []
    
    def _get_static_geo_estimate(self, from_loc: str, to_loc: str) -> Dict[str, Any]:
        """Return static transit estimates for common routes."""
        from_lower = from_loc.lower()
        to_lower = to_loc.lower()
        
        # Japan routes
        if ("tokyo" in from_lower and "kyoto" in to_lower) or ("kyoto" in from_lower and "tokyo" in to_lower):
            return {
                "distance_km": 513,
                "duration_minutes": 135,  # Shinkansen
                "mode": "shinkansen",
                "estimated_cost_usd": 100,
                "notes": "Nozomi Shinkansen - fastest option"
            }
        
        if ("tokyo" in from_lower and "osaka" in to_lower) or ("osaka" in from_lower and "tokyo" in to_lower):
            return {
                "distance_km": 515,
                "duration_minutes": 150,
                "mode": "shinkansen",
                "estimated_cost_usd": 95,
                "notes": "Hikari Shinkansen"
            }
        
        if ("kyoto" in from_lower and "osaka" in to_lower) or ("osaka" in from_lower and "kyoto" in to_lower):
            return {
                "distance_km": 56,
                "duration_minutes": 15,
                "mode": "local_train",
                "estimated_cost_usd": 5,
                "notes": "Keihan or Hankyu line"
            }
        
        # Default unknown route
        return {
            "distance_km": 100,
            "duration_minutes": 120,
            "mode": "unknown",
            "estimated_cost_usd": 50,
            "notes": "Generic estimate - real data needed"
        }
    
    def _get_static_price_band(self, category: str, city: str, band: str) -> Tuple[float, str]:
        """Return static price estimates for common cities worldwide."""
        city_lower = city.lower()
        band_lower = band.lower()
        cat_lower = category.lower()

        def build_prices(hotel, food, activity, transport):
            return {
                "hotel": {"budget": (hotel[0], "Budget accommodation"), "moderate": (hotel[1], "Mid-range hotel"), "expensive": (hotel[2], "Upscale hotel"), "luxury": (hotel[3], "Luxury hotel")},
                "food":  {"budget": (food[0], "Street food / casual"), "moderate": (food[1], "Mid-range dining"), "expensive": (food[2], "Upscale dining"), "luxury": (food[3], "Fine dining")},
                "activity": {"budget": (activity[0], "Free sights / parks"), "moderate": (activity[1], "Museums / tours"), "expensive": (activity[2], "Premium experiences"), "luxury": (activity[3], "Private tours")},
                "transport": {"budget": (transport[0], "Public transit"), "moderate": (transport[1], "Taxi / rideshare"), "expensive": (transport[2], "Inter-city travel"), "luxury": (transport[3], "Private car")},
            }

        # ── Japan ─────────────────────────────────────────────────────────────
        if any(c in city_lower for c in ["tokyo", "kyoto", "osaka", "japan"]):
            prices = build_prices([50,120,250,500], [15,40,80,200], [0,20,80,300], [5,20,100,300])
            return prices.get(cat_lower, {}).get(band_lower, (50, "Japan estimate"))

        # ── Scandinavia ────────────────────────────────────────────────────────
        if any(c in city_lower for c in ["stockholm","gothenburg","malmo","sweden",
                                          "oslo","bergen","norway",
                                          "copenhagen","denmark",
                                          "helsinki","finland",
                                          "reykjavik","iceland"]):
            prices = build_prices([70,160,320,650], [25,60,120,280], [5,25,90,350], [10,30,120,400])
            return prices.get(cat_lower, {}).get(band_lower, (70, "Scandinavia estimate"))

        # ── Western Europe ─────────────────────────────────────────────────────
        if any(c in city_lower for c in ["paris","rome","barcelona","london","amsterdam",
                                          "berlin","madrid","lisbon","prague","vienna",
                                          "zurich","geneva","brussels","dublin"]):
            prices = build_prices([60,150,300,600], [20,50,100,250], [5,20,75,300], [8,25,100,350])
            return prices.get(cat_lower, {}).get(band_lower, (60, "Western Europe estimate"))

        # ── SE Asia ────────────────────────────────────────────────────────────
        if any(c in city_lower for c in ["bangkok","phuket","chiang mai","thailand",
                                          "singapore",
                                          "bali","jakarta","indonesia",
                                          "kuala lumpur","malaysia",
                                          "hanoi","ho chi minh","vietnam",
                                          "manila","philippines"]):
            prices = build_prices([20,55,120,350], [5,15,40,100], [3,15,50,200], [3,12,60,200])
            return prices.get(cat_lower, {}).get(band_lower, (25, "SE Asia estimate"))

        # ── USA / Canada ───────────────────────────────────────────────────────
        if any(c in city_lower for c in ["new york","los angeles","chicago","miami",
                                          "san francisco","boston","seattle",
                                          "toronto","vancouver","montreal"]):
            prices = build_prices([80,180,350,700], [20,55,110,250], [10,30,100,400], [10,35,150,500])
            return prices.get(cat_lower, {}).get(band_lower, (80, "North America estimate"))

        # ── Middle East ────────────────────────────────────────────────────────
        if any(c in city_lower for c in ["dubai","abu dhabi","qatar","doha",
                                          "istanbul","turkey"]):
            prices = build_prices([60,150,300,800], [15,40,90,250], [10,25,80,400], [10,30,100,500])
            return prices.get(cat_lower, {}).get(band_lower, (60, "Middle East estimate"))

        # ── South Asia ─────────────────────────────────────────────────────────
        if any(c in city_lower for c in ["mumbai","delhi","bangalore","kolkata","india",
                                          "kathmandu","nepal",
                                          "colombo","sri lanka"]):
            prices = build_prices([15,50,120,350], [5,15,35,100], [2,10,40,150], [3,10,50,200])
            return prices.get(cat_lower, {}).get(band_lower, (20, "South Asia estimate"))

        # ── Africa ─────────────────────────────────────────────────────────────
        if any(c in city_lower for c in ["cape town","johannesburg","south africa",
                                          "nairobi","kenya",
                                          "marrakech","morocco",
                                          "cairo","egypt"]):
            prices = build_prices([30,80,180,400], [10,25,60,150], [5,20,60,250], [5,20,80,300])
            return prices.get(cat_lower, {}).get(band_lower, (35, "Africa estimate"))

        # ── Latin America ──────────────────────────────────────────────────────
        if any(c in city_lower for c in ["mexico city","cancun","mexico",
                                          "buenos aires","argentina",
                                          "rio de janeiro","sao paulo","brazil",
                                          "bogota","colombia","lima","peru"]):
            prices = build_prices([25,70,150,350], [8,20,50,150], [5,15,50,200], [5,15,60,250])
            return prices.get(cat_lower, {}).get(band_lower, (30, "Latin America estimate"))

        # ── Default fallback ───────────────────────────────────────────────────
        prices = build_prices([40,100,220,500], [12,35,75,180], [5,20,65,250], [5,20,80,300])
        return prices.get(cat_lower, {}).get(band_lower, (50, f"Generic estimate for {city}"))


    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_call_log(self) -> List[Dict[str, Any]]:
        """Get the call log for observability/debugging."""
        return self._call_log.copy()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "entries": len(self._cache),
            "keys": list(self._cache.keys())
        }
    
    def clear_cache(self):
        """Clear the tool cache."""
        self._cache.clear()
    
    def clear_log(self):
        """Clear the call log."""
        self._call_log.clear()
