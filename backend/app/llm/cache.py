"""
Simple in-memory response cache to reduce token usage.
Used with Groq to stay within 100k tokens/day limit.
"""

import time
from typing import Optional, Any, Dict, Tuple
from functools import lru_cache as functools_lru_cache


class ResponseCache:
    """
    In-memory cache for LLM responses.
    
    Reduces token consumption by caching identical prompts.
    TTL-based expiration to prevent stale data.
    """
    
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        """
        Initialize cache.
        
        Args:
            ttl_seconds: Time-to-live for cache entries
            max_size: Maximum number of entries (LRU eviction)
        """
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, prompt: str, model: str, temperature: float) -> str:
        """Create cache key from request parameters."""
        import hashlib
        key_string = f"{model}:{temperature}:{prompt}"
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]
    
    def get(self, prompt: str, model: str, temperature: float = 0.1) -> Optional[Any]:
        """
        Get cached response if available and not expired.
        
        Args:
            prompt: The input prompt
            model: Model name
            temperature: Temperature setting
            
        Returns:
            Cached response or None
        """
        key = self._make_key(prompt, model, temperature)
        
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                self._hits += 1
                return value
            else:
                # Expired
                del self._cache[key]
        
        self._misses += 1
        return None
    
    def set(self, prompt: str, model: str, response: Any, temperature: float = 0.1):
        """
        Cache a response.
        
        Args:
            prompt: The input prompt
            model: Model name
            response: Response to cache
            temperature: Temperature setting
        """
        key = self._make_key(prompt, model, temperature)
        
        # LRU eviction if at capacity
        if len(self._cache) >= self._max_size:
            # Remove oldest entry
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
        
        self._cache[key] = (response, time.time())
    
    def clear(self):
        """Clear all cached entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "entries": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "ttl_seconds": self._ttl,
            "max_size": self._max_size,
        }
    
    def estimate_savings(self, avg_tokens_per_request: int = 3000) -> Dict[str, Any]:
        """
        Estimate token savings from caching.
        
        Args:
            avg_tokens_per_request: Average tokens saved per cache hit
            
        Returns:
            Savings statistics
        """
        tokens_saved = self._hits * avg_tokens_per_request
        
        return {
            "tokens_saved": tokens_saved,
            "estimated_cost_saved_usd": round(tokens_saved / 1000 * 0.002, 4),
            "cache_hits": self._hits,
        }


# Global cache instance
_cache_instance: Optional[ResponseCache] = None


def get_cache(ttl_seconds: int = 3600) -> ResponseCache:
    """Get or create the global response cache."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ResponseCache(ttl_seconds=ttl_seconds)
    return _cache_instance
