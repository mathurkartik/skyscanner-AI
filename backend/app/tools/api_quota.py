"""
API Quota Tracking & Circuit Breaker Utilities (AG-123, AG-124).
Provides resilience against downstream API rate limits, outages, and credit exhaustion.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"        # Normal operation: requests pass through
    OPEN = "open"            # Failing: immediately reject requests
    HALF_OPEN = "half_open"  # Trial mode: test if service recovered


class CircuitBreakerOpenException(Exception):
    """Raised when request is attempted while circuit breaker is OPEN."""
    pass


class CircuitBreaker:
    """
    Resilient circuit breaker for external API integrations (AG-123).
    Transitions from CLOSED -> OPEN on consecutive failures,
    then to HALF_OPEN after recovery_timeout to probe health.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.consecutive_successes = 0
        self.last_failure_time = 0.0

    def can_execute(self) -> bool:
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_failure_time > self.recovery_timeout_seconds:
                logger.info("CircuitBreaker '%s': Entering HALF_OPEN state.", self.name)
                self.state = CircuitState.HALF_OPEN
                self.consecutive_successes = 0
                return True
            return False
        return True

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.consecutive_successes += 1
            if self.consecutive_successes >= self.success_threshold:
                logger.info("CircuitBreaker '%s': Recovered! Transitioning HALF_OPEN -> CLOSED.", self.name)
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.consecutive_successes = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self) -> None:
        self.last_failure_time = time.time()
        if self.state == CircuitState.HALF_OPEN:
            logger.warning("CircuitBreaker '%s': Probe failed in HALF_OPEN. Transitioning back to OPEN.", self.name)
            self.state = CircuitState.OPEN
            self.failure_count += 1
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                logger.warning(
                    "CircuitBreaker '%s': %d consecutive failures reached. Transitioning CLOSED -> OPEN.",
                    self.name,
                    self.failure_count,
                )
                self.state = CircuitState.OPEN

    async def call(self, fn: Callable, *args, **kwargs) -> Any:
        if not self.can_execute():
            raise CircuitBreakerOpenException(
                f"Circuit breaker '{self.name}' is OPEN. Requests temporarily rejected."
            )
        try:
            if asyncio.iscoroutinefunction(fn):
                result = await fn(*args, **kwargs)
            else:
                result = fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise e


class QuotaTracker:
    """
    Sliding window API request and quota tracker (AG-124).
    Tracks live usage against daily or hourly caps per provider.
    """

    DEFAULT_LIMITS = {
        "rapidapi": 500,        # 500 req/day
        "google_places": 1000,  # 1000 req/day
        "gemini": 1500,         # 1500 req/day
        "groq": 2000,           # 2000 req/day
        "kiwi": 500,            # 500 req/day
    }

    def __init__(self, limits: Optional[Dict[str, int]] = None, window_seconds: float = 86400.0):
        self.limits = limits or dict(self.DEFAULT_LIMITS)
        self.window_seconds = window_seconds
        self._requests: Dict[str, list[float]] = {}
        self._rejected_counts: Dict[str, int] = {}

    def _prune(self, service: str, now: float) -> list[float]:
        timestamps = self._requests.get(service, [])
        cutoff = now - self.window_seconds
        valid = [t for t in timestamps if t > cutoff]
        self._requests[service] = valid
        return valid

    def can_request(self, service: str) -> bool:
        now = time.time()
        valid = self._prune(service, now)
        limit = self.limits.get(service, 10000)
        return len(valid) < limit

    def record_request(self, service: str) -> bool:
        now = time.time()
        valid = self._prune(service, now)
        limit = self.limits.get(service, 10000)
        if len(valid) >= limit:
            self._rejected_counts[service] = self._rejected_counts.get(service, 0) + 1
            logger.warning("Quota limit reached for service '%s' (%d/%d).", service, len(valid), limit)
            return False
        valid.append(now)
        self._requests[service] = valid
        return True

    def get_usage(self, service: str) -> Dict[str, Any]:
        now = time.time()
        valid = self._prune(service, now)
        limit = self.limits.get(service, 10000)
        return {
            "service": service,
            "used": len(valid),
            "limit": limit,
            "remaining": max(0, limit - len(valid)),
            "rejected": self._rejected_counts.get(service, 0),
        }

    def get_all_usage(self) -> Dict[str, Dict[str, Any]]:
        services = set(list(self.limits.keys()) + list(self._requests.keys()))
        return {s: self.get_usage(s) for s in sorted(services)}


_GLOBAL_QUOTA_TRACKER = QuotaTracker()
_CIRCUIT_BREAKERS: Dict[str, CircuitBreaker] = {}


def get_quota_tracker() -> QuotaTracker:
    return _GLOBAL_QUOTA_TRACKER


def get_circuit_breaker(service: str) -> CircuitBreaker:
    if service not in _CIRCUIT_BREAKERS:
        _CIRCUIT_BREAKERS[service] = CircuitBreaker(name=service)
    return _CIRCUIT_BREAKERS[service]

