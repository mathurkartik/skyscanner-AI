"""
Unit tests for ResponseCache (AG-120).
Tests TTL expiration, LRU eviction, and hit/miss statistics.
"""

import time
import pytest
from app.llm.cache import ResponseCache


def test_cache_hit_and_miss():
    """Test standard cache set and get operations."""
    cache = ResponseCache(ttl_seconds=60, max_size=10)
    
    # Initial get should be a miss
    assert cache.get("prompt 1", "gpt-4") is None
    stats = cache.get_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 0

    # Set value
    cache.set("prompt 1", "gpt-4", "response 1")
    
    # Next get should be a hit
    result = cache.get("prompt 1", "gpt-4")
    assert result == "response 1"
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["entries"] == 1
    assert stats["hit_rate_percent"] == 50.0


def test_cache_ttl_expiration():
    """Test that items expire when their age exceeds ttl_seconds."""
    cache = ResponseCache(ttl_seconds=1, max_size=10)
    cache.set("short_lived", "model-x", "temp_value")
    
    # Immediately accessible
    assert cache.get("short_lived", "model-x") == "temp_value"
    
    # Wait for expiration
    time.sleep(1.1)
    
    # Should now be expired and return None
    assert cache.get("short_lived", "model-x") is None
    assert cache.get_stats()["entries"] == 0


def test_cache_lru_eviction():
    """Test that oldest entry is evicted when capacity is reached."""
    cache = ResponseCache(ttl_seconds=60, max_size=3)
    
    cache.set("p1", "m", "r1")
    time.sleep(0.01)
    cache.set("p2", "m", "r2")
    time.sleep(0.01)
    cache.set("p3", "m", "r3")
    assert cache.get_stats()["entries"] == 3
    
    # Adding a 4th entry should evict p1 (the oldest)
    cache.set("p4", "m", "r4")
    assert cache.get_stats()["entries"] == 3
    assert cache.get("p1", "m") is None
    assert cache.get("p2", "m") == "r2"
    assert cache.get("p3", "m") == "r3"
    assert cache.get("p4", "m") == "r4"


def test_cache_clear():
    """Test that clear resets all data and statistics."""
    cache = ResponseCache(ttl_seconds=60, max_size=10)
    cache.set("a", "m", "1")
    cache.set("b", "m", "2")
    cache.get("a", "m")
    
    cache.clear()
    stats = cache.get_stats()
    assert stats["entries"] == 0
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["hit_rate_percent"] == 0.0

