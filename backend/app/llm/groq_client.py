"""
Groq LLM Client with token tracking and structured output support.
Optimized for 100k tokens/day limit.
"""

import asyncio
import json
import re
import time
from typing import Optional, Any, Dict, Type, TypeVar
from functools import lru_cache

try:
    from groq import Groq
except ImportError:
    Groq = None

from ..config import get_settings
from ..models import TravelConstraints, ActivityCatalog, BudgetBreakdown
from .token_tracker import get_token_tracker, TokenBudgetExceeded

T = TypeVar('T')


class GroqClient:
    """
    Groq LLM client with token tracking, caching, and structured output.
    
    Features:
    - Token budget checking before requests
    - Response caching to reduce repeated calls
    - Structured JSON output validation
    - Automatic retry on rate limits
    - Fallback to stub/mock for testing
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 900,
        temperature: float = 0.1,
        enable_tracking: bool = True,
        enable_cache: bool = True,
    ):
        settings = get_settings()
        
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self._primary_blocked_until = 0.0
        self.max_tokens = max_tokens or settings.groq_max_tokens_per_request
        self.temperature = temperature or settings.groq_temperature
        self.enable_tracking = enable_tracking and settings.enable_token_tracking
        self.enable_cache = enable_cache and settings.enable_response_cache
        
        # Initialize Groq client if available
        if Groq and self.api_key:
            self._client = Groq(api_key=self.api_key)
        else:
            self._client = None
        
        # Token tracker
        if self.enable_tracking:
            from .token_tracker import TokenTracker
            self._tracker = get_token_tracker(settings.token_buffer_percent)
        else:
            self._tracker = None
        
        # Cache (simple in-memory)
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = settings.cache_ttl_seconds
    
    def _get_cache_key(self, prompt: str, model: str) -> str:
        """Generate cache key from prompt and model."""
        import hashlib
        key = f"{model}:{prompt}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def _check_cache(self, prompt: str, model: str) -> Optional[Any]:
        """Check for cached response."""
        if not self.enable_cache:
            return None
        
        key = self._get_cache_key(prompt, model)
        if key in self._cache:
            cached, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return cached
            else:
                del self._cache[key]
        return None
    
    def _set_cache(self, prompt: str, model: str, response: Any):
        """Cache a response."""
        if self.enable_cache:
            key = self._get_cache_key(prompt, model)
            self._cache[key] = (response, time.time())
    
    def _check_token_budget(self, estimated_tokens: int) -> bool:
        """Check if we have enough tokens for this request."""
        if not self.enable_tracking or not self._tracker:
            return True
        return self._tracker.can_make_request(estimated_tokens)
    
    def _record_usage(self, prompt_tokens: int, completion_tokens: int):
        """Record token usage if tracking is enabled."""
        if self.enable_tracking and self._tracker:
            self._tracker.record_usage(prompt_tokens, completion_tokens, self.model)
    
    async def extract_constraints(
        self,
        natural_language_request: str
    ) -> TravelConstraints:
        """
        Phase 2: Extract TravelConstraints from natural language.
        
        Uses structured output with JSON schema for reliable parsing.
        """
        if not self._client:
            raise RuntimeError("Groq client not initialized. Check GROQ_API_KEY.")
        
        # Check token budget (extraction ~3k tokens)
        estimated_tokens = self._tracker.estimate_request_cost(
            len(natural_language_request) + 2000,  # Prompt + system message
            expected_response_length=1500
        ) if self._tracker else 3000
        
        if not self._check_token_budget(estimated_tokens):
            summary = self._tracker.get_usage_summary() if self._tracker else {}
            raise TokenBudgetExceeded(
                requested=estimated_tokens,
                remaining=summary.get("remaining", 0),
                limit=summary.get("daily_limit", 100000)
            )
        
        # Check cache
        cache_key_prompt = f"constraints:{natural_language_request}"
        cached = self._check_cache(cache_key_prompt, self.model)
        if cached and isinstance(cached, TravelConstraints):
            print(f"Cache hit for: {natural_language_request[:50]}...")
            return cached
        print(f"Extracting constraints for: {natural_language_request}")
        
        # Build structured extraction prompt
        system_prompt = """You are a travel planning assistant. Extract structured travel constraints from the user's request.

Respond with valid JSON matching this schema:
{
  "destination_region": "Country or region name, or null if not mentioned",
  "cities": ["Stop1", "Stop2", ...],
  "duration_days": number or null,
  "budget_total": number or null,
  "budget_tier": "budget, moderate, luxury, or null",
  "currency": "3-letter code like INR, USD, EUR (default to USD or INR)",
  "preferences": ["what they want to experience"],
  "avoidances": ["what they want to avoid"],
  "hard_requirements": ["must-haves inferred from request"],
  "soft_preferences": ["nice-to-haves inferred"],
  "is_road_trip": boolean
}

CRITICAL EXTRACTION RULES (STRICT - DO NOT INVENT MISSING DATA):
- Destination: Extract the primary destination/country/city. If user does NOT state where they want to go, set destination_region to null and cities to [].
- Duration: Extract duration in days (e.g. 1 week = 7 days). If user does NOT mention duration or days, set duration_days to null.
- Budget:
  * If a numeric budget is stated ($2000, 50000 INR, etc.), extract the number into budget_total and the 3-letter currency into currency.
  * If user specifies a budget style without an exact number (e.g., "cheap", "backpacking", "budget trip" -> "budget"; "moderate", "mid-range", "reasonable" -> "moderate"; "luxury", "5-star", "lavish" -> "luxury"), set budget_tier to "budget", "moderate", or "luxury".
  * If neither amount nor tier is mentioned, set budget_total to null and budget_tier to null.
  * DO NOT guess or invent default budget or duration values if omitted.

TRIP TYPE DETECTION:
- ROAD TRIP countries (Iceland, Norway, New Zealand, Scotland, Ireland, Portugal coast, South Africa Garden Route, Australia outback):
  Set is_road_trip=true. Generate 4-8 ROUTE STOPS (regions/towns along the route), NOT just the capital.
  Example Iceland: cities=["Reykjavik","Vik","Hofn","Egilsstadir","Akureyri","Snaefellsnes"]
  Example Norway: cities=["Oslo","Bergen","Geiranger","Alesund","Tromso"]
  Example New Zealand: cities=["Auckland","Rotorua","Wellington","Queenstown","Milford Sound"]

- CITY TRIP destinations (Paris, Tokyo, NYC, Dubai, Singapore):
  Set is_road_trip=false. Use 1-3 cities as appropriate.

- MULTI-CITY countries (Japan, Italy, Spain):
  Set is_road_trip=false. Generate 2-4 key cities.
  Example Japan: cities=["Tokyo","Kyoto","Osaka"]

- Preferences: include nature, adventure, scenic drives, temples, food etc. based on request.
- For road trips: add "self-drive", "scenic routes", "nature" to preferences automatically.
"""

        try:
            content = await self.chat_with_retry(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": natural_language_request}
                ],
                max_tokens=1500,
            )
            content = self._extract_json(content)
            data = json.loads(content)
            constraints = TravelConstraints.model_validate(data)
            
            # Cache result
            self._set_cache(cache_key_prompt, self.model, constraints)
            
            return constraints
            
        except TokenBudgetExceeded:
            raise
        except Exception as e:
            # Log error with context
            raise RuntimeError(f"Failed to extract constraints: {str(e)}")
    
    async def generate_with_schema(
        self,
        prompt: str,
        system_prompt: str,
        output_schema: Type[T],
        max_tokens: Optional[int] = None
    ) -> T:
        """
        Generic structured generation with Pydantic schema validation.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            output_schema: Pydantic model class for validation
            max_tokens: Override default max tokens
            
        Returns:
            Validated Pydantic model instance
        """
        if not self._client:
            raise RuntimeError("Groq client not initialized")
        
        # Estimate and check budget
        estimated = self._tracker.estimate_request_cost(
            len(prompt) + len(system_prompt),
            expected_response_length=2000
        ) if self._tracker else 4000
        
        if not self._check_token_budget(estimated):
            summary = self._tracker.get_usage_summary() if self._tracker else {}
            raise TokenBudgetExceeded(
                requested=estimated,
                remaining=summary.get("remaining", 0),
                limit=summary.get("daily_limit", 100000)
            )
        
        # Check cache
        cached = self._check_cache(prompt, self.model)
        if cached and isinstance(cached, output_schema):
            return cached
        
        try:
            content = await self.chat_with_retry(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens or 2000,
            )
            content = self._extract_json(content)
            data = json.loads(content)
            result = output_schema.model_validate(data)
            
            # Cache result
            self._set_cache(prompt, self.model, result)
            
            return result
            
        except Exception as e:
            raise RuntimeError(f"Generation failed: {str(e)}")
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response that may contain markdown fences or preamble."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            start = 1
            end = len(lines)
            for i in range(1, len(lines)):
                if lines[i].strip() == "```":
                    end = i
                    break
            text = "\n".join(lines[start:end]).strip()
        brace = text.find("{")
        bracket = text.find("[")
        if brace == -1 and bracket == -1:
            return text
        if brace == -1:
            start = bracket
        elif bracket == -1:
            start = brace
        else:
            start = min(brace, bracket)
        return text[start:]

    async def chat_with_retry(
        self,
        messages: list,
        max_tokens: int = 900,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
        max_retries: int = 6,
    ) -> str:
        """Chat completion with automatic retry on 429 rate limit errors."""
        if not self._client:
            raise RuntimeError("Groq client not initialized")
        settings = get_settings()
        max_tokens = min(max_tokens, settings.groq_max_tokens_per_request)
        fallback = settings.groq_fallback_model
        for attempt in range(max_retries):
            # Groq rate limits are per model, so use the fallback while the primary's daily quota is exhausted
            model = fallback if (fallback and time.time() < self._primary_blocked_until) else self.model
            try:
                kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature or self.temperature,
                    "max_tokens": max_tokens,
                }
                # gpt-oss spends hidden reasoning tokens that count against the 8k TPM free-tier limit
                if "gpt-oss" in model:
                    kwargs["reasoning_effort"] = "low"
                response = await asyncio.to_thread(self._client.chat.completions.create, **kwargs)
                if response.usage:
                    self._record_usage(response.usage.prompt_tokens, response.usage.completion_tokens)
                return response.choices[0].message.content
            except Exception as e:
                msg = str(e)
                if "429" in msg or "rate_limit" in msg:
                    match = re.search(r"try again in (?:(\d+)h)?(?:(\d+)m)?([\d.]+)s", msg)
                    wait = (int(match.group(1) or 0) * 3600 + int(match.group(2) or 0) * 60 + float(match.group(3)) + 1) if match else 5 * (attempt + 1)
                    if "tokens per day" in msg and model == self.model and fallback and fallback != model:
                        self._primary_blocked_until = time.time() + wait
                        print(f"Daily quota hit on {model}; using {fallback} for {wait:.0f}s")
                        continue
                    wait = min(wait, 30)
                    print(f"Rate limited, waiting {wait:.1f}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait)
                    continue
                raise
        raise RuntimeError("Max retries exceeded for rate limit")

    def get_token_summary(self) -> Dict[str, Any]:
        """Get current token usage summary."""
        if self._tracker:
            return self._tracker.get_usage_summary()
        return {"tracking_disabled": True}


# Global instance
_groq_client: Optional[GroqClient] = None


def get_groq_client() -> GroqClient:
    """Get or create the global Groq client."""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client
