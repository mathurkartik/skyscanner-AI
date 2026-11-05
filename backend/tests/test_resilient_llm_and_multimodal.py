"""
Tests for ResilientLLMClient and Multi-Modal Transport Architecture (Spec v3).
Verifies provider failover, multi-modal transport modes (train, flight, bus, drive, ferry),
and end-to-end integration across Logistics and Orchestrator agents.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.resilient_client import ResilientLLMClient
from app.models.schemas import (
    TravelConstraints,
    TransportSegment,
    LogisticsOutput,
    DraftItinerary,
    FinalItinerary,
    BudgetBreakdown,
    ReviewStatus,
)
from app.agents.logistics import LogisticsAgent
from app.agents.orchestrator import OrchestratorAgent


@pytest.mark.asyncio
async def test_resilient_llm_client_primary_success():
    """Verify ResilientLLMClient uses primary provider when it succeeds."""
    client = ResilientLLMClient()
    mock_primary = MagicMock()
    mock_primary.chat_with_retry = AsyncMock(return_value="Primary response")
    mock_fallback = MagicMock()
    mock_fallback.chat_with_retry = AsyncMock(return_value="Fallback response")

    client._primary_client = mock_primary
    client._fallback_clients = [mock_fallback]

    res = await client.chat_with_retry(messages=[{"role": "user", "content": "Hi"}])
    assert res == "Primary response"
    mock_primary.chat_with_retry.assert_awaited_once()
    mock_fallback.chat_with_retry.assert_not_awaited()


@pytest.mark.asyncio
async def test_resilient_llm_client_failover_to_secondary():
    """Verify ResilientLLMClient fails over when primary encounters RateLimit/Error."""
    client = ResilientLLMClient()
    mock_primary = MagicMock()
    mock_primary.chat_with_retry = AsyncMock(side_effect=RuntimeError("Rate limit exceeded 429"))
    mock_fallback = MagicMock()
    mock_fallback.chat_with_retry = AsyncMock(return_value="Secondary Groq response")

    client._primary_client = mock_primary
    client._fallback_clients = [mock_fallback]

    res = await client.chat_with_retry(messages=[{"role": "user", "content": "Hi"}])
    assert res == "Secondary Groq response"
    mock_primary.chat_with_retry.assert_awaited_once()
    mock_fallback.chat_with_retry.assert_awaited_once()


@pytest.mark.asyncio
async def test_logistics_agent_generates_multi_modal_transport():
    """Verify Logistics Agent produces multi-modal transit segments (Getting There & Inter-City)."""
    agent = LogisticsAgent()

    constraints = TravelConstraints(
        destination_region="Switzerland",
        cities=["Zurich", "Lucerne"],
        duration_days=5,
        budget_total=2500,
        currency="USD",
        preferences=["train travel", "scenic mountains"],
        avoidances=[]
    )

    logistics = await agent.plan(constraints)
    assert len(logistics.transport_segments) > 0

    first_segment = logistics.transport_segments[0]
    assert isinstance(first_segment, TransportSegment)
    assert first_segment.from_city != ""
    assert first_segment.to_city != ""
    assert first_segment.recommended_mode in ["flight", "train", "bus", "drive", "ferry"]
    assert first_segment.estimated_duration_hours > 0
    assert first_segment.booking_url is not None


@pytest.mark.asyncio
async def test_orchestrator_multi_modal_integration():
    """Verify Orchestrator integrates transport_segments from Logistics into FinalItinerary."""
    orchestrator = OrchestratorAgent()

    constraints = TravelConstraints(
        destination_region="Japan",
        cities=["Tokyo", "Kyoto"],
        duration_days=6,
        budget_total=3000,
        currency="USD",
        preferences=["shinkansen", "bullet train", "temples"],
        avoidances=[]
    )

    train_seg = TransportSegment(
        from_city="Tokyo",
        to_city="Kyoto",
        recommended_mode="train",
        reason="Tokaido Shinkansen bullet train takes 2h 15m",
        estimated_duration_hours=2.25,
        estimated_cost_usd=110.0,
        operator_name="JR Central (Nozomi)",
        line_or_flight_number="Nozomi 225",
        booking_url="https://www.thetrainline.com/book/results?origin=Tokyo&destination=Kyoto"
    )

    dummy_logistics = LogisticsOutput(
        lodging_plans=[],
        movement_plans=[],
        day_skeletons=[],
        total_estimated_transit_hours=2.25,
        transport_segments=[train_seg]
    )

    from app.models.schemas import ActivityCatalog, Activity, ActivityType, CostBand
    act = Activity(
        id="act-tokyo-sensoji",
        name="Senso-ji Temple",
        city="Tokyo",
        type=ActivityType.TEMPLE,
        cost_band=CostBand.BUDGET,
        estimated_duration_hours=2.0,
        rationale="Top historic landmark matching cultural interest",
        description="Historic temple in Asakusa"
    )
    dummy_catalog = ActivityCatalog(activities=[act], per_city={"Tokyo": [act.id]}, neighborhood_notes={})
    from app.models.schemas import BudgetBreakdown, BudgetCategory
    dummy_budget = BudgetBreakdown(
        categories=[BudgetCategory(category="transport", estimated_total=110.0, currency="USD", percent_of_total=100.0)],
        grand_total=110.0,
        currency="USD",
        within_budget=True,
        remaining_buffer=2890.0
    )

    draft = await orchestrator.merge(constraints, dummy_catalog, dummy_logistics, dummy_budget)
    assert len(draft.transport_segments) == 1
    assert draft.transport_segments[0].recommended_mode == "train"

    final = orchestrator._draft_to_final(draft, constraints, dummy_budget)
    assert isinstance(final, FinalItinerary)
    assert len(final.transport_segments) == 1
    assert final.transport_segments[0].operator_name == "JR Central (Nozomi)"
    assert "thetrainline.com" in final.transport_segments[0].booking_url
