"""
Unit tests for TripStructuringAgent (AG-119).
Verifies single city, multi-city allocations, pace determinations, and edge cases.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.trip_structuring import TripStructuringAgent
from app.models.schemas import TravelConstraints, TripStructure, Region


@pytest.fixture
def structuring_agent():
    return TripStructuringAgent()


@pytest.mark.asyncio
async def test_trip_structuring_single_city(structuring_agent, sample_single_city_constraints):
    """Test structuring with a single city destination."""
    result = await structuring_agent.structure(sample_single_city_constraints)
    assert result is not None
    assert len(result.regions) == 1
    assert result.regions[0].base_location == "Paris"
    assert result.regions[0].days == 3
    assert sum(r.days for r in result.regions) == 3


@pytest.mark.asyncio
async def test_trip_structuring_multi_city(structuring_agent, sample_constraints):
    """Test structuring with multiple cities distributes days correctly."""
    result = await structuring_agent.structure(sample_constraints)
    assert result is not None
    assert len(result.regions) == 2
    total_allocated = sum(r.days for r in result.regions)
    assert total_allocated == sample_constraints.duration_days
    locations = [r.base_location for r in result.regions]
    assert "Tokyo" in locations
    assert "Kyoto" in locations


@pytest.mark.asyncio
async def test_trip_structuring_empty_cities_fallback(structuring_agent):
    """Test empty cities array falls back gracefully to destination_region without division error (AG-088)."""
    constraints = TravelConstraints(
        destination_region="Iceland",
        cities=[],
        duration_days=5,
        budget_total=2000.0,
        currency="USD",
    )
    result = await structuring_agent.structure(constraints)
    assert result is not None
    assert len(result.regions) >= 1
    assert result.regions[0].base_location == "Iceland"
    assert sum(r.days for r in result.regions) == 5


def test_determine_pace_guards(structuring_agent):
    """Test _determine_pace handles 0 or negative inputs gracefully (AG-088)."""
    # Duration <= 0 or num_regions <= 0 returns balanced
    assert structuring_agent._determine_pace(0, 5) == "balanced"
    assert structuring_agent._determine_pace(5, 0) == "balanced"
    assert structuring_agent._determine_pace(-1, -1) == "balanced"
    # ratio = duration / num_regions
    # ratio >= 3: relaxed
    assert structuring_agent._determine_pace(6, 2) == "relaxed"
    # ratio >= 2: balanced
    assert structuring_agent._determine_pace(5, 2) == "balanced"
    # ratio < 2: aggressive
    assert structuring_agent._determine_pace(3, 3) == "aggressive"


@pytest.mark.asyncio
async def test_trip_structuring_with_llm():
    """Test LLM-based region generation when LLM client is available."""
    mock_llm = MagicMock()
    llm_json = """{
        "trip_type": "multi_region",
        "regions": [
            {"name": "Kanto", "base_location": "Tokyo", "days": 5, "highlights": ["Shibuya", "Asakusa"]},
            {"name": "Kansai", "base_location": "Kyoto", "days": 5, "highlights": ["Gion", "Arashiyama"]}
        ],
        "route": ["Tokyo", "Kyoto"],
        "pace": "balanced"
    }"""
    mock_llm.chat_with_retry = AsyncMock(return_value=llm_json)
    agent = TripStructuringAgent(llm_client=mock_llm)
    
    constraints = TravelConstraints(
        destination_region="Japan",
        cities=["Tokyo", "Kyoto"],
        duration_days=10,
        budget_total=4000.0,
        currency="USD",
    )
    result = await agent.structure(constraints)
    assert result.pace == "balanced"
    assert len(result.regions) == 2
    assert result.route == ["Tokyo", "Kyoto"]
