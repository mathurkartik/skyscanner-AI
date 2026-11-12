"""
Unit tests for DestinationAgent and destination research helpers (AG-077, AG-042, AG-043).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.schemas import (
    TravelConstraints,
    ActivityCatalog,
    Activity,
    ActivityType,
    CrowdLevel,
    CostBand,
    PlaceInfo,
)
from app.agents.destination import DestinationAgent, _matches_place_name


def test_matches_place_name_word_boundaries_ag042():
    """Verify word-boundary matching prevents false positives like 'Art' matching 'Kart racing'."""
    assert _matches_place_name("Art", "Kart racing in Shibuya") is False
    assert _matches_place_name("Museum of Art", "Smart Kart Tour") is False

    assert _matches_place_name("Senso-ji", "Senso-ji Temple") is True
    assert _matches_place_name("Louvre", "Musée du Louvre") is True
    assert _matches_place_name("Eiffel Tower", "eiffel tower") is True

    assert _matches_place_name("", "Eiffel Tower") is False
    assert _matches_place_name("Eiffel Tower", "") is False


def test_avoidance_filtering_with_domain_synonyms_ag043():
    """Verify avoidances check tags, name, description, rationale, with domain synonyms (alcohol -> wine/beer/etc.)."""
    agent = DestinationAgent()

    activities = [
        Activity(
            id="act-wine-1",
            name="Wine Tasting and Cellar Tour",
            city="Paris",
            type=ActivityType.CULTURE,
            cost_band=CostBand.MODERATE,
            crowd_level=CrowdLevel.LOW,
            estimated_duration_hours=2.0,
            tags=["drinks", "food"],
            description="Sample premier grand cru vintages.",
            rationale="Authentic winery experience."
        ),
        Activity(
            id="act-louvre-2",
            name="Louvre Museum Guided Walk",
            city="Paris",
            type=ActivityType.MUSEUM,
            cost_band=CostBand.MODERATE,
            crowd_level=CrowdLevel.HIGH,
            estimated_duration_hours=3.0,
            tags=["art", "museum"],
            description="Explore classic Renaissance art.",
            rationale="World renowned collection."
        ),
        Activity(
            id="act-brewery-3",
            name="Craft Brewery Experience",
            city="Paris",
            type=ActivityType.FOOD,
            cost_band=CostBand.BUDGET,
            crowd_level=CrowdLevel.MEDIUM,
            estimated_duration_hours=1.5,
            tags=["beverages"],
            description="Tour the local artisanal brewhouse.",
            rationale="Beer brewing culture."
        ),
        Activity(
            id="act-garden-4",
            name="Botanical Garden Promenade",
            city="Paris",
            type=ActivityType.NATURE,
            cost_band=CostBand.BUDGET,
            crowd_level=CrowdLevel.LOW,
            estimated_duration_hours=1.0,
            tags=["nature", "parks"],
            description="Relaxed garden stroll with native flora.",
            rationale="Peaceful scenic retreat."
        )
    ]

    filtered = agent._filter_avoidances(activities, ["alcohol"])
    names = [a.name for a in filtered]
    assert "Wine Tasting and Cellar Tour" not in names
    assert "Craft Brewery Experience" not in names
    assert "Louvre Museum Guided Walk" in names
    assert "Botanical Garden Promenade" in names


def test_avoidance_filtering_crowds():
    """Verify avoidance of heavy crowds filters activities with High crowd levels or crowd descriptions."""
    agent = DestinationAgent()

    activities = [
        Activity(
            id="act-shibuya-1",
            name="Crowded Shibuya Crossing Rush",
            city="Tokyo",
            type=ActivityType.CULTURE,
            cost_band=CostBand.BUDGET,
            crowd_level=CrowdLevel.HIGH,
            estimated_duration_hours=0.5,
            tags=["iconic"],
            description="Packed with huge crowds during peak hour.",
            rationale="Famous intersection."
        ),
        Activity(
            id="act-zen-2",
            name="Quiet Zen Garden Meditation",
            city="Tokyo",
            type=ActivityType.CULTURE,
            cost_band=CostBand.BUDGET,
            crowd_level=CrowdLevel.LOW,
            estimated_duration_hours=1.0,
            tags=["peaceful", "zen"],
            description="Secluded courtyard temple.",
            rationale="Serene morning escape."
        )
    ]

    filtered = agent._filter_avoidances(activities, ["crowds"])
    names = [a.name for a in filtered]
    assert "Crowded Shibuya Crossing Rush" not in names
    assert "Quiet Zen Garden Meditation" in names


@pytest.mark.asyncio
async def test_destination_agent_research_with_mock_llm():
    """Verify DestinationAgent researches cities using LLM response and enriches with Google Places."""
    mock_llm = MagicMock()
    mock_llm.chat_with_retry = AsyncMock(return_value="""{
        "activities": [
            {
                "name": "Eiffel Tower Summit",
                "type": "culture",
                "cost_band": "moderate",
                "crowd_level": "high",
                "estimated_duration_hours": 2.0,
                "tags": ["iconic", "views"],
                "description": "Ascend to the top deck of the Eiffel Tower.",
                "rationale": "Iconic landmark of Paris.",
                "address": "Champ de Mars",
                "estimated_cost_usd": 30.0
            },
            {
                "name": "Seine River Sunset Walk",
                "type": "nature",
                "cost_band": "budget",
                "crowd_level": "low",
                "estimated_duration_hours": 1.0,
                "tags": ["scenic", "walk"],
                "description": "Leisurely stroll along the Seine quays.",
                "rationale": "Romantic atmosphere and illuminated bridges.",
                "address": "Quai de la Seine",
                "estimated_cost_usd": 0.0
            }
        ]
    }""")

    mock_places = MagicMock()
    mock_places.search_text = AsyncMock(return_value=[
        PlaceInfo(
            name="Eiffel Tower",
            rating=4.7,
            review_count=180000,
            address="Champ de Mars, 5 Av. Anatole France, 75007 Paris",
            lat=48.8584,
            lng=2.2945,
            is_estimate=False
        )
    ])

    agent = DestinationAgent(llm_client=mock_llm, places_client=mock_places)
    constraints = TravelConstraints(
        origin="LHR",
        destination_region="France",
        duration_days=3,
        cities=["Paris"],
        budget_total=1500.0,
        currency="EUR",
        preferences=["sightseeing", "romance"],
        avoidances=["alcohol"]
    )

    catalog = await agent.research(constraints)

    assert isinstance(catalog, ActivityCatalog)
    assert "Paris" in catalog.per_city
    assert len(catalog.activities) >= 2

    eiffel = next((a for a in catalog.activities if "Eiffel" in a.name), None)
    assert eiffel is not None
    # Rationale enriched with Google Places rating and review count
    assert "4.7" in eiffel.rationale or "180,000" in eiffel.rationale


@pytest.mark.asyncio
async def test_destination_agent_fallback_when_llm_fails():
    """Verify DestinationAgent falls back to generic catalog when LLM raises exception."""
    mock_llm = MagicMock()
    mock_llm.chat_with_retry = AsyncMock(side_effect=RuntimeError("LLM API unavailable"))

    mock_places = MagicMock()
    mock_places.search_text = AsyncMock(return_value=[])

    agent = DestinationAgent(llm_client=mock_llm, places_client=mock_places)
    constraints = TravelConstraints(
        origin="JFK",
        destination_region="Iceland",
        duration_days=3,
        cities=["Reykjavik"],
        budget_total=2000.0,
        currency="USD"
    )

    catalog = await agent.research(constraints)
    assert isinstance(catalog, ActivityCatalog)
    assert "Reykjavik" in catalog.per_city
    assert len(catalog.activities) > 0
    assert any("Explore" in a.name or "Reykjavik" in a.name for a in catalog.activities)
