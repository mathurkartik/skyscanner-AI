"""
Pytest Shared Fixtures for Skyscanner AI Backend (AG-122).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.config import Settings
from app.main import app
from app.models.schemas import (
    TravelConstraints,
    FinalItinerary,
    PlanResponse,
    DraftItinerary,
    DayItinerary,
    DayItineraryItem,
    ActivityType,
    BudgetBreakdown,
)


@pytest.fixture
def mock_llm_client():
    """Shared mock LLM client with chat and chat_with_retry."""
    client = MagicMock()
    client.chat = AsyncMock(return_value="Mock LLM response")
    client.chat_with_retry = AsyncMock(return_value="Mock LLM response with retry")
    client.count_tokens = MagicMock(return_value=42)
    return client


@pytest.fixture
def sample_constraints() -> TravelConstraints:
    """Standard 5-day Japan travel constraints."""
    return TravelConstraints(
        destination_region="Japan",
        cities=["Tokyo", "Kyoto"],
        duration_days=5,
        budget_total=3000.0,
        currency="USD",
        pace="balanced",
        preferences=["culture", "temples", "food"],
        origin_city="New York",
        travel_dates="2026-10-01 to 2026-10-05",
    )


@pytest.fixture
def sample_single_city_constraints() -> TravelConstraints:
    """Standard 3-day Paris travel constraints."""
    return TravelConstraints(
        destination_region="France",
        cities=["Paris"],
        duration_days=3,
        budget_total=1500.0,
        currency="EUR",
        pace="relaxed",
        preferences=["art", "cafes", "museums"],
        origin_city="London",
        travel_dates="2026-11-01 to 2026-11-04",
    )


@pytest.fixture
def sample_draft_itinerary(sample_constraints) -> DraftItinerary:
    """Minimal draft itinerary for testing agents."""
    day1 = DayItinerary(
        day_number=1,
        city="Tokyo",
        items=[
            DayItineraryItem(
                slot_index=0,
                time="09:00 - 12:00",
                activity_name="Senso-ji Temple",
                city="Tokyo",
                type=ActivityType.CULTURE,
                cost_estimate=0.0,
            ),
            DayItineraryItem(
                slot_index=1,
                time="13:00 - 16:00",
                activity_name="Tokyo Skytree",
                city="Tokyo",
                type=ActivityType.SIGHTSEEING,
                cost_estimate=25.0,
            ),
        ],
        day_summary="Day 1: Historic Asakusa and Modern Skytree",
        day_cost=25.0,
    )
    return DraftItinerary(
        days=[day1],
        total_cost=25.0,
        status="draft",
    )


@pytest.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async test client for FastAPI routes."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
