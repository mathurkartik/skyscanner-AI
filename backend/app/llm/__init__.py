"""
LLM Client module — supports Groq (default) and Gemini (fallback).
Provides unified interface with token tracking and caching.
"""

from .groq_client import GroqClient, get_groq_client
from .gemini_client import GeminiClient, get_gemini_client
from .resilient_client import ResilientLLMClient, get_resilient_llm_client
from .token_tracker import TokenTracker, get_token_tracker, TokenBudgetExceeded
from .cache import ResponseCache, get_cache


def get_llm_client():
    """Return the resilient multi-provider LLM client with auto-failover."""
    from ..config import get_settings
    settings = get_settings()
    if getattr(settings, "llm_failover", True):
        return get_resilient_llm_client()
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        return get_gemini_client()
    return get_groq_client()


__all__ = [
    "GroqClient",
    "get_groq_client",
    "GeminiClient",
    "get_gemini_client",
    "ResilientLLMClient",
    "get_resilient_llm_client",
    "get_llm_client",
    "TokenTracker",
    "get_token_tracker",
    "TokenBudgetExceeded",
    "ResponseCache",
    "get_cache",
]
