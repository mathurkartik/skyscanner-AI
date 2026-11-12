"""
Unit tests for ToolRouter (AG-121).
Tests search, geo estimation, price bands, FX conversion, cache eviction, and logging.
"""

import pytest
from app.tools.router import ToolRouter


@pytest.fixture
def router():
    return ToolRouter()


@pytest.mark.asyncio
async def test_tool_router_search(router):
    """Test destination search returns results for known queries."""
    results = await router.search("temples in kyoto")
    assert isinstance(results, list)
    assert len(results) > 0
    assert "title" in results[0]
    assert "url" in results[0]


@pytest.mark.asyncio
async def test_tool_router_geo_estimate(router):
    """Test distance and transit time estimation between locations."""
    geo = await router.geo_estimate("Tokyo", "Kyoto")
    assert "distance_km" in geo
    assert "duration_minutes" in geo
    assert geo["duration_minutes"] > 0
    assert "mode" in geo


@pytest.mark.asyncio
async def test_tool_router_price_band(router):
    """Test price range lookups across categories and tiers."""
    band = await router.price_band("hotel", "Tokyo", "moderate")
    assert "estimate_usd" in band
    assert band["estimate_usd"] > 0
    assert band["currency"] == "USD"
    assert band["category"] == "hotel"


@pytest.mark.asyncio
async def test_tool_router_fx_convert(router):
    """Test currency conversion tool using unified FX rates."""
    fx = await router.fx_convert(100.0, "USD", "EUR")
    assert fx["original_currency"] == "USD"
    assert fx["target_currency"] == "EUR"
    assert fx["converted_amount"] > 0
    assert fx["rate"] > 0


@pytest.mark.asyncio
async def test_tool_router_cache_eviction():
    """Test that cache size is strictly bounded by CACHE_MAX_ITEMS."""
    router = ToolRouter()
    router.CACHE_MAX_ITEMS = 5
    
    for i in range(10):
        router._set_cache(f"key_{i}", f"val_{i}")
        
    assert len(router._cache) <= 5
    # The oldest keys (key_0 through key_4) should have been evicted
    assert "key_0" not in router._cache
    assert "key_9" in router._cache


@pytest.mark.asyncio
async def test_tool_router_call_log(router):
    """Test that tool calls are logged with trace_id for observability."""
    router._call_log.clear()
    await router.search("temples in kyoto", trace_id="trace-123")
    assert len(router._call_log) >= 1
    assert router._call_log[-1]["tool"] == "search"
    assert router._call_log[-1]["trace_id"] == "trace-123"
