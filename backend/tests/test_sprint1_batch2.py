"""
Unit tests for Sprint 1 Batch 2 (LLM Token Efficiency and Output Reliability).
Covers:
- AG-009: Static airport IATA lookup table (500+ commercial passenger airports)
- AG-010: Configurable Gemini max_tokens (raised from 2000 to 4096)
- AG-011: Removed duplicate _extract_json in GeminiClient
- AG-017: LLM JSON schema validation and missing-field logging
- AG-018: Flight LLM prompt max_tokens increased to 1200
"""

import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import Settings
from app.llm.gemini_client import GeminiClient
from app.llm.llm_utils import validate_llm_json, validate_item_fields
from app.tools.airports import lookup_iata_code, AIRPORT_LOOKUP
from app.tools.flight_client import resolve_iata, FlightClient


def test_ag009_static_airport_database_size():
    """Verify static airport database contains over 500 major commercial passenger airports."""
    assert len(AIRPORT_LOOKUP) >= 500
    # Spot-check major global hubs
    assert AIRPORT_LOOKUP["delhi"] == "DEL"
    assert AIRPORT_LOOKUP["london"] == "LHR"
    assert AIRPORT_LOOKUP["tokyo"] == "HND"
    assert AIRPORT_LOOKUP["new york"] == "JFK"
    assert AIRPORT_LOOKUP["reykjavik"] == "KEF"
    assert AIRPORT_LOOKUP["jaipur"] == "JAI"
    assert AIRPORT_LOOKUP["paris"] == "CDG"
    assert AIRPORT_LOOKUP["dubai"] == "DXB"
    assert AIRPORT_LOOKUP["singapore"] == "SIN"
    assert AIRPORT_LOOKUP["sydney"] == "SYD"


def test_ag009_lookup_iata_code():
    """Verify lookup_iata_code handles case sensitivity, whitespace, and aliases."""
    assert lookup_iata_code("  Jaipur  ") == "JAI"
    assert lookup_iata_code("tokyo") in ("HND", "NRT")
    assert lookup_iata_code("Reykjavik, Iceland") == "KEF"
    assert lookup_iata_code("UNKNOWN_CITY_XYZ_123") is None


@pytest.mark.asyncio
async def test_ag009_resolve_iata_uses_static_lookup_without_llm():
    """resolve_iata should immediately resolve cities from static lookup without invoking LLM."""
    with patch("app.llm.get_llm_client") as mock_get_llm:
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        code = await resolve_iata("Jaipur")
        assert code == "JAI"
        mock_llm.chat_with_retry.assert_not_called()

        code2 = await resolve_iata("Reykjavik")
        assert code2 == "KEF"
        mock_llm.chat_with_retry.assert_not_called()


def test_ag010_gemini_max_tokens_config():
    """Verify gemini_max_tokens is configurable and defaults to 4096."""
    settings = Settings()
    assert hasattr(settings, "gemini_max_tokens")
    assert settings.gemini_max_tokens == 4096

    client = GeminiClient(api_key="test_key")
    assert client.max_tokens == 4096


def test_ag011_single_extract_json_in_gemini():
    """Verify GeminiClient only has a single clean _extract_json implementation delegating to extract_json_from_text."""
    client = GeminiClient(api_key="test_key")
    raw_markdown = "```json\n{\"destination\": \"Kyoto\", \"status\": \"ok\"}\n```"
    result = client._extract_json(raw_markdown)
    assert '{"destination": "Kyoto", "status": "ok"}' in result


def test_ag017_validate_llm_json(caplog):
    """Verify validate_llm_json validates types, required keys, and logs warnings appropriately."""
    with caplog.at_level(logging.WARNING):
        # Valid dictionary
        valid_dict = {"activities": [{"name": "Eiffel Tower"}]}
        assert validate_llm_json(valid_dict, required_keys=["activities"], caller_name="TestAgent") is True
        assert len(caplog.records) == 0

        # Missing required key
        invalid_dict = {"wrong_key": 123}
        assert validate_llm_json(invalid_dict, required_keys=["activities"], caller_name="TestAgent") is False
        assert any("missing expected fields: ['activities']" in r.message for r in caplog.records)

        # Type mismatch
        caplog.clear()
        assert validate_llm_json(["not_a_dict"], expected_type=dict, caller_name="TestAgent") is False
        assert any("LLM output type mismatch: expected dict, got list" in r.message for r in caplog.records)


def test_ag017_validate_item_fields(caplog):
    """Verify validate_item_fields checks required fields on dictionary items."""
    with caplog.at_level(logging.WARNING):
        valid_item = {"name": "Louvre", "city": "Paris"}
        assert validate_item_fields(valid_item, ["name", "city"], caller_name="TestAgent") is True

        # Missing key
        caplog.clear()
        invalid_item = {"city": "Paris"}
        assert validate_item_fields(invalid_item, ["name", "city"], caller_name="TestAgent") is False
        assert any("missing fields: ['name']" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_ag018_flight_llm_prompt_max_tokens():
    """Verify FlightClient._generate_llm_flights passes max_tokens=1200 to LLM client."""
    client = FlightClient()
    mock_llm = MagicMock()
    mock_llm.chat_with_retry = AsyncMock(
        return_value='[{"airline": "Air A", "price": 450, "currency": "USD"}, {"airline": "Air B", "price": 520, "currency": "USD"}]'
    )

    with patch("app.llm.get_llm_client", return_value=mock_llm):
        offers = await client._generate_llm_flights("DEL", "LHR", "2026-12-01", "2026-12-10", cabin_class="economy", adults=1, currency="USD")
        assert len(offers) == 2
        assert mock_llm.chat_with_retry.called
        kwargs = mock_llm.chat_with_retry.call_args.kwargs
        assert kwargs.get("max_tokens") == 1200
