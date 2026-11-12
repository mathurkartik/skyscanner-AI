"""
Unit tests for TokenTracker (AG-080).
Tests token accumulation, safety buffer calculation, budget limits, and usage summary.
"""

import pytest
from app.llm.token_tracker import TokenTracker, TokenUsage


def test_token_tracker_initialization_and_safety_buffer():
    """Verify default 20% safety buffer gives 80,000 effective limit for 100,000 daily limit."""
    tracker = TokenTracker(buffer_percent=20)
    assert tracker.DAILY_LIMIT == 100000
    assert tracker.effective_limit == 80000
    assert tracker.remaining_tokens == 80000
    assert tracker.percent_used == 0.0


def test_token_tracker_record_usage_and_budget_check():
    """Verify recording token usage updates remaining tokens and percent used accurately."""
    tracker = TokenTracker(buffer_percent=20)

    # Can make request for 5000 tokens
    assert tracker.can_make_request(5000) is True

    # Record 5000 prompt + 3000 completion = 8000 tokens
    usage = tracker.record_usage(5000, 3000, "llama-3.3-70b-versatile")
    assert usage.total_tokens == 8000
    assert tracker.remaining_tokens == 72000
    assert tracker.percent_used == 8.0

    # Record additional 70,000 tokens
    tracker.record_usage(50000, 20000, "llama-3.3-70b-versatile")
    assert tracker.remaining_tokens == 2000

    # Request for 5000 tokens should now be rejected as it exceeds effective limit (80,000)
    assert tracker.can_make_request(5000) is False
    # But request for 1500 tokens should still be allowed
    assert tracker.can_make_request(1500) is True


def test_token_tracker_summary_by_model():
    """Verify usage summary groups statistics by model and reports counts."""
    tracker = TokenTracker(buffer_percent=10)
    tracker.record_usage(1000, 500, "llama-3.3-70b-versatile")
    tracker.record_usage(2000, 1000, "llama-3.1-8b-instant")

    summary = tracker.get_usage_summary()
    assert summary["daily_total"] == 4500
    assert summary["request_count"] == 2
    assert summary["effective_limit"] == 90000
    assert "llama-3.3-70b-versatile" in summary["by_model"]
    assert "llama-3.1-8b-instant" in summary["by_model"]
    assert summary["by_model"]["llama-3.3-70b-versatile"]["tokens"] == 1500
    assert summary["by_model"]["llama-3.1-8b-instant"]["tokens"] == 3000

