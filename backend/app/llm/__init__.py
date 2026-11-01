"""
LLM Client module — supports Groq (default) and Gemini (fallback).
Provides unified interface with token tracking and caching.
"""

from .groq_client import GroqClient, get_groq_client
from .gemini_client import GeminiClient, get_gemini_client
from .token_tracker import TokenTracker, get_token_tracker, TokenBudgetExceeded
from .cache import ResponseCache, get_cache


def get_llm_client():
    """Return the configured LLM client based on LLM_PROVIDER env var."""
    from ..config import get_settings
    settings = get_settings()
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        return get_gemini_client()
    if settings.llm_provider == "groq" and settings.groq_api_key:
        return get_groq_client()
    if settings.gemini_api_key:
        return get_gemini_client()
    return get_groq_client()


__all__ = [
    "GroqClient",
    "get_groq_client",
    "GeminiClient",
    "get_gemini_client",
    "get_llm_client",
    "TokenTracker",
    "get_token_tracker",
    "TokenBudgetExceeded",
    "ResponseCache",
    "get_cache",
]
