"""
Token usage tracking for Groq (100k tokens/day limit).
Provides daily budget management with safety buffers.
"""

import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from functools import lru_cache


class TokenUsage:
    """Tracks usage for a single request."""
    
    def __init__(self, prompt_tokens: int, completion_tokens: int, model: str):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens
        self.model = model
        self.timestamp = datetime.now(timezone.utc)


class TokenTracker:
    """
    Tracks daily token usage against Groq's 100k limit.
    
    Features:
    - Thread-safe token counting
    - Daily reset at midnight UTC
    - Configurable safety buffer (default 20%)
    - Per-request tracking with model info
    """
    
    DAILY_LIMIT = 100000  # Groq free tier: 100k tokens/day
    
    def __init__(self, buffer_percent: int = 20):
        self._lock = threading.RLock()
        self._usage_history: list[TokenUsage] = []
        self._daily_total = 0
        self._buffer_percent = buffer_percent
        self._day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
    def _reset_if_new_day(self):
        """Reset counter if we've crossed midnight UTC."""
        current_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        if current_day > self._day_start:
            with self._lock:
                self._daily_total = 0
                self._day_start = current_day
                self._usage_history = []
    
    @property
    def effective_limit(self) -> int:
        """Limit minus safety buffer."""
        return int(self.DAILY_LIMIT * (1 - self._buffer_percent / 100))
    
    @property
    def remaining_tokens(self) -> int:
        """Tokens remaining within effective limit."""
        self._reset_if_new_day()
        with self._lock:
            return max(0, self.effective_limit - self._daily_total)
    
    @property
    def percent_used(self) -> float:
        """Percentage of daily limit used."""
        self._reset_if_new_day()
        with self._lock:
            return (self._daily_total / self.DAILY_LIMIT) * 100
    
    def can_make_request(self, estimated_tokens: int = 15000) -> bool:
        """
        Check if we can make a request without exceeding budget.
        
        Args:
            estimated_tokens: Expected token usage for this request
            
        Returns:
            True if request should proceed, False if it would exceed budget
        """
        self._reset_if_new_day()
        with self._lock:
            return (self._daily_total + estimated_tokens) <= self.effective_limit
    
    def record_usage(self, prompt_tokens: int, completion_tokens: int, model: str) -> TokenUsage:
        """
        Record actual token usage from a request.
        
        Args:
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            model: Model name used
            
        Returns:
            TokenUsage record
        """
        self._reset_if_new_day()
        usage = TokenUsage(prompt_tokens, completion_tokens, model)
        
        with self._lock:
            self._usage_history.append(usage)
            self._daily_total += usage.total_tokens
            
        return usage
    
    def get_usage_summary(self) -> dict:
        """Get current usage statistics."""
        self._reset_if_new_day()
        with self._lock:
            if not self._usage_history:
                return {
                    "daily_total": 0,
                    "remaining": self.effective_limit,
                    "percent_used": 0.0,
                    "daily_limit": self.DAILY_LIMIT,
                    "effective_limit": self.effective_limit,
                    "buffer_percent": self._buffer_percent,
                    "request_count": 0,
                }
            
            # Group by model
            model_usage = {}
            for usage in self._usage_history:
                if usage.model not in model_usage:
                    model_usage[usage.model] = {"requests": 0, "tokens": 0}
                model_usage[usage.model]["requests"] += 1
                model_usage[usage.model]["tokens"] += usage.total_tokens
            
            return {
                "daily_total": self._daily_total,
                "remaining": self.remaining_tokens,
                "percent_used": self.percent_used,
                "daily_limit": self.DAILY_LIMIT,
                "effective_limit": self.effective_limit,
                "buffer_percent": self._buffer_percent,
                "request_count": len(self._usage_history),
                "by_model": model_usage,
                "next_reset": (self._day_start + timedelta(days=1)).isoformat(),
            }
    
    def estimate_request_cost(
        self,
        prompt_length_chars: int,
        expected_response_length: int = 2000,
        model: str = "mixtral-8x7b-32768"
    ) -> int:
        """
        Estimate token cost for a request.
        
        Rough approximation: 4 chars ≈ 1 token for English text.
        
        Args:
            prompt_length_chars: Length of input prompt
            expected_response_length: Expected response length in chars
            model: Model to use (affects tokenization slightly)
            
        Returns:
            Estimated total tokens
        """
        prompt_tokens = prompt_length_chars // 4
        response_tokens = expected_response_length // 4
        return prompt_tokens + response_tokens


# Global instance (per-process, reset on restart)
_token_tracker: Optional[TokenTracker] = None
_token_tracker_lock = threading.Lock()


def get_token_tracker(buffer_percent: int = 20) -> TokenTracker:
    """Get or create the global token tracker."""
    global _token_tracker
    if _token_tracker is None:
        with _token_tracker_lock:
            if _token_tracker is None:
                _token_tracker = TokenTracker(buffer_percent=buffer_percent)
    return _token_tracker


class TokenBudgetExceeded(Exception):
    """Raised when a request would exceed the daily token budget."""
    
    def __init__(self, requested: int, remaining: int, limit: int):
        self.requested = requested
        self.remaining = remaining
        self.limit = limit
        super().__init__(
            f"Token budget exceeded: requested {requested}, "
            f"remaining {remaining}, daily limit {limit}"
        )
