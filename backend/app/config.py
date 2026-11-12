"""Application configuration."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # App
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:4200,http://localhost:5173,http://localhost:5174,http://localhost:3000"
    
    # Skyscanner & Travel APIs
    rapidapi_key: str | None = None
    skyscanner_api_key: str | None = None
    duffel_api_key: str | None = None
    google_places_api_key: str | None = None
    kiwi_api_key: str | None = None
    opentripmap_api_key: str | None = None
    enable_rapidapi: bool = False  # Disabled by default: use authentic built-in routing and Google Places
    
    # LLM Provider (gemini, groq)
    llm_provider: str = "gemini"

    # Groq Configuration (Default — worked reliably for 7 months)
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_max_tokens_per_request: int = 4000
    groq_fallback_model: str | None = "openai/gpt-oss-20b"
    groq_temperature: float = 0.1  # Low for structured extraction

    # Gemini Configuration (Fallback / Primary)
    gemini_api_key: str | None = None
    gemini_api_key_2: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    gemini_max_tokens: int = 4096  # AG-010: Configurable max output tokens (raised from 2000 to 4096)
    llm_failover: bool = True
    
    # Token Budget Management (Groq = 100k tokens/day)
    enable_token_tracking: bool = True
    max_tokens_per_plan_request: int = 15000  # Safety limit per travel plan
    token_buffer_percent: int = 20  # Keep 20% buffer for daily limit
    
    # Agents
    agent_timeout_seconds: int = 120
    max_review_retries: int = 3
    
    # Caching to reduce token usage
    enable_response_cache: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    
    # Tools (stubs for now)
    enable_web_search: bool = False
    enable_geo_routing: bool = False
    enable_pricing_api: bool = False
    enable_fx_api: bool = False
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
