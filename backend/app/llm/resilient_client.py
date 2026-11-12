"""
Resilient LLM Client — Dual-provider orchestrator with automatic failover.
Seamlessly routes requests between Gemini (high-throughput primary) and Groq (reliable fallback),
with support for secondary Gemini accounts.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar

from ..config import get_settings
from ..models import TravelConstraints
from .token_tracker import TokenBudgetExceeded
from .cache import get_cache

logger = logging.getLogger(__name__)
T = TypeVar("T")


class ResilientLLMClient:
    """
    Dual-provider LLM client implementing auto-failover between Gemini and Groq.
    Compatible drop-in replacement for GroqClient and GeminiClient.
    """

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self._cache = get_cache(ttl_seconds=getattr(self.settings, "cache_ttl_seconds", 3600))
        self._primary_client = None
        self._fallback_clients: List[Any] = []
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize available LLM providers in priority order."""
        from .gemini_client import GeminiClient
        from .groq_client import GroqClient

        all_clients = []

        # Gemini Account 1
        if self.settings.gemini_api_key:
            try:
                c1 = GeminiClient(
                    api_key=self.settings.gemini_api_key,
                    model=self.settings.gemini_model,
                )
                all_clients.append(("gemini_1", c1))
            except Exception as e:
                logger.warning("Failed to initialize Gemini Client 1: %s", e)

        # Gemini Account 2 (double quota)
        if getattr(self.settings, "gemini_api_key_2", None):
            try:
                c2 = GeminiClient(
                    api_key=self.settings.gemini_api_key_2,
                    model=self.settings.gemini_model,
                )
                all_clients.append(("gemini_2", c2))
            except Exception as e:
                logger.warning("Failed to initialize Gemini Client 2: %s", e)

        # Groq Client
        if self.settings.groq_api_key:
            try:
                cg = GroqClient(
                    api_key=self.settings.groq_api_key,
                    model=self.settings.groq_model,
                )
                all_clients.append(("groq", cg))
            except Exception as e:
                logger.warning("Failed to initialize Groq Client: %s", e)

        # Sort according to preferred provider
        pref = (self.settings.llm_provider or "groq").lower()
        if pref == "gemini":
            ordered = [c for c in all_clients if c[0].startswith("gemini")] + [c for c in all_clients if c[0] == "groq"]
        else:
            ordered = [c for c in all_clients if c[0] == "groq"] + [c for c in all_clients if c[0].startswith("gemini")]

        if ordered:
            self._primary_client = ordered[0][1]
            self._fallback_clients = [c[1] for c in ordered[1:]]
        else:
            # Default to singleton groq client even if key might be loaded later
            self._primary_client = GroqClient()

    @property
    def model(self) -> str:
        if self._primary_client:
            return getattr(self._primary_client, "model", "default")
        return "default"

    async def chat_with_retry(
        self,
        messages: list,
        max_tokens: int = 900,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """Attempt primary provider; on failure/rate-limit, fail over to backup provider."""
        import hashlib
        import json
        try:
            msg_str = json.dumps(messages, sort_keys=True)
        except Exception:
            msg_str = str(messages)
        prompt_key = hashlib.sha256(msg_str.encode("utf-8")).hexdigest()
        if getattr(self.settings, "enable_response_cache", True):
            cached = self._cache.get(prompt_key, self.model, temperature or 0.1)
            if cached is not None:
                return cached

        clients = [self._primary_client] + self._fallback_clients if getattr(self.settings, "llm_failover", True) else [self._primary_client]

        last_err = None
        for client in clients:
            if not client:
                continue
            try:
                result = await client.chat_with_retry(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                if getattr(self.settings, "enable_response_cache", True) and result:
                    self._cache.set(prompt_key, self.model, result, temperature or 0.1)
                return result
            except Exception as err:
                last_err = err
                logger.warning(
                    "LLM provider %s failed (%s). Failing over to next provider...",
                    type(client).__name__,
                    err
                )

        raise RuntimeError(f"All LLM providers failed. Last error: {last_err}") from last_err

    async def extract_constraints(self, natural_language_request: str) -> TravelConstraints:
        """Extract constraints with auto-failover across providers."""
        cache_key = f"constraints:{natural_language_request.strip().lower()}"
        if getattr(self.settings, "enable_response_cache", True):
            cached = self._cache.get(cache_key, self.model)
            if cached is not None and isinstance(cached, TravelConstraints):
                return cached

        clients = [self._primary_client] + self._fallback_clients if getattr(self.settings, "llm_failover", True) else [self._primary_client]

        last_err = None
        for client in clients:
            if not client:
                continue
            try:
                result = await client.extract_constraints(natural_language_request)
                if getattr(self.settings, "enable_response_cache", True) and result:
                    self._cache.set(cache_key, self.model, result)
                return result
            except Exception as err:
                last_err = err
                logger.warning(
                    "Constraint extraction failed on %s (%s). Failing over...",
                    type(client).__name__,
                    err
                )

        raise RuntimeError(f"All LLM providers failed to extract constraints: {last_err}") from last_err

    async def generate_with_schema(
        self,
        prompt: str,
        system_prompt: str,
        output_schema: Type[T],
        max_tokens: Optional[int] = None
    ) -> T:
        """Structured generation with auto-failover."""
        clients = [self._primary_client] + self._fallback_clients if getattr(self.settings, "llm_failover", True) else [self._primary_client]

        last_err = None
        for client in clients:
            if not client:
                continue
            try:
                return await client.generate_with_schema(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    output_schema=output_schema,
                    max_tokens=max_tokens
                )
            except Exception as err:
                last_err = err
                logger.warning(
                    "generate_with_schema failed on %s (%s). Failing over...",
                    type(client).__name__,
                    err
                )

        raise RuntimeError(f"All LLM providers failed for schema generation: {last_err}") from last_err

    def get_token_summary(self) -> Dict[str, Any]:
        """Aggregate token usage summary."""
        if self._primary_client and hasattr(self._primary_client, "get_token_summary"):
            return self._primary_client.get_token_summary()
        return {"tracking_disabled": True}


_resilient_client_instance: Optional[ResilientLLMClient] = None


def get_resilient_llm_client() -> ResilientLLMClient:
    """Get singleton ResilientLLMClient."""
    global _resilient_client_instance
    if _resilient_client_instance is None:
        _resilient_client_instance = ResilientLLMClient()
    return _resilient_client_instance

