"""
Unit tests for GroqClient and ResilientLLMClient (AG-079, AG-045, AG-046).
Covers retry loops, backoff caps, SHA-256 hashed cache keys, and provider failover.
"""

import pytest
import asyncio
import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.groq_client import GroqClient
from app.llm.resilient_client import ResilientLLMClient


@pytest.mark.asyncio
async def test_groq_client_retry_capped_at_3_and_10s_backoff_ag045():
    """Verify GroqClient retry loop caps at 3 retries and max wait at 10s."""
    client = GroqClient(api_key="test_key")
    client._client = MagicMock()

    # Mock chat.completions.create to raise 429 rate limit
    mock_create = MagicMock(side_effect=Exception("429 rate_limit: please try again in 45s"))
    client._client.chat.completions.create = mock_create

    sleep_calls = []
    async def mock_sleep(seconds):
        sleep_calls.append(seconds)

    with patch("asyncio.sleep", side_effect=mock_sleep):
        with pytest.raises(RuntimeError, match="Max retries exceeded for rate limit"):
            await client.chat_with_retry(
                messages=[{"role": "user", "content": "hi"}],
                max_retries=3
            )

    # Must have attempted 3 times
    assert mock_create.call_count == 3
    # All sleeps must be capped at 10s (min(45, 10))
    for s in sleep_calls:
        assert s <= 10.0


@pytest.mark.asyncio
async def test_resilient_llm_cache_key_sha256_ag046():
    """Verify ResilientLLMClient computes SHA-256 cache key from json-serialized messages."""
    messages = [
        {"role": "system", "content": "You are a planner."},
        {"role": "user", "content": "Plan a trip to Japan."}
    ]

    expected_json = json.dumps(messages, sort_keys=True)
    expected_hash = hashlib.sha256(expected_json.encode("utf-8")).hexdigest()

    mock_cache = MagicMock()
    mock_cache.get = MagicMock(return_value="Cached response from Tokyo")

    client = ResilientLLMClient()
    client._cache = mock_cache

    res = await client.chat_with_retry(messages=messages)
    assert res == "Cached response from Tokyo"
    mock_cache.get.assert_called_once()
    args, _ = mock_cache.get.call_args
    # First arg must be the sha256 hash
    assert args[0] == expected_hash


@pytest.mark.asyncio
async def test_resilient_llm_auto_failover_on_primary_failure():
    """Verify ResilientLLMClient fails over to secondary client when primary raises error."""
    primary_mock = MagicMock()
    primary_mock.chat_with_retry = AsyncMock(side_effect=RuntimeError("Primary Groq rate limited"))

    fallback_mock = MagicMock()
    fallback_mock.chat_with_retry = AsyncMock(return_value="Fallback Gemini Response")

    client = ResilientLLMClient()
    client._primary_client = primary_mock
    client._fallback_clients = [fallback_mock]
    client._cache = MagicMock()
    client._cache.get = MagicMock(return_value=None)
    client._cache.set = MagicMock()

    messages = [{"role": "user", "content": "test failover"}]
    res = await client.chat_with_retry(messages=messages)

    assert res == "Fallback Gemini Response"
    primary_mock.chat_with_retry.assert_called_once()
    fallback_mock.chat_with_retry.assert_called_once()
