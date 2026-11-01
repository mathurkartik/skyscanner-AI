"""
Gemini LLM Client using the google-genai SDK.
Same interface as GroqClient: chat_with_retry, extract_constraints, generate_with_schema.
"""

import asyncio
import json
import time
from typing import Optional, Any, Dict, Type, TypeVar

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

from ..config import get_settings
from ..models import TravelConstraints
from .token_tracker import get_token_tracker, TokenBudgetExceeded

T = TypeVar('T')


class GeminiClient:
    """
    Gemini LLM client implementing the same interface as GroqClient.
    Drop-in replacement: chat_with_retry, extract_constraints, generate_with_schema.
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

        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.max_tokens = max_tokens or settings.groq_max_tokens_per_request
        self.temperature = temperature or settings.groq_temperature
        self.enable_tracking = enable_tracking and settings.enable_token_tracking
        self.enable_cache = enable_cache and settings.enable_response_cache

        self._client = None
        if genai and self.api_key:
            self._client = genai.Client(api_key=self.api_key)

        if self.enable_tracking:
            self._tracker = get_token_tracker(settings.token_buffer_percent)
        else:
            self._tracker = None

        self._cache: Dict[str, Any] = {}
        self._cache_ttl = settings.cache_ttl_seconds

    def _get_cache_key(self, prompt: str, model: str) -> str:
        import hashlib
        key = f"{model}:{prompt}"
        return hashlib.md5(key.encode()).hexdigest()

    def _check_cache(self, prompt: str, model: str) -> Optional[Any]:
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
        if self.enable_cache:
            key = self._get_cache_key(prompt, model)
            self._cache[key] = (response, time.time())

    def _check_token_budget(self, estimated_tokens: int) -> bool:
        if not self.enable_tracking or not self._tracker:
            return True
        return self._tracker.can_make_request(estimated_tokens)

    def _record_usage(self, prompt_tokens: int, completion_tokens: int):
        if self.enable_tracking and self._tracker:
            self._tracker.record_usage(prompt_tokens, completion_tokens, self.model)

    def _get_response_text(self, response) -> str:
        """Robustly extract text from a Gemini response object."""
        # Try .text first (works when response has exactly one text part)
        try:
            if response.text:
                return response.text
        except (AttributeError, ValueError):
            pass

        # Fall back to manual candidate extraction
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and candidate.content:
                parts = getattr(candidate.content, 'parts', None)
                if parts:
                    for part in parts:
                        text = getattr(part, 'text', None)
                        if text:
                            return text

        # Check if blocked by safety
        if hasattr(response, 'prompt_feedback'):
            feedback = response.prompt_feedback
            block_reason = getattr(feedback, 'block_reason', None)
            if block_reason:
                raise RuntimeError(f"Gemini blocked the request: {block_reason}")

        raise RuntimeError(
            f"Gemini returned no text. "
            f"Candidates: {len(response.candidates) if hasattr(response, 'candidates') and response.candidates else 0}"
        )

    def _extract_json(self, text: str) -> str:
        """Extract JSON from Gemini response, stripping markdown fences if present."""
        if not text:
            raise RuntimeError("Empty text passed to JSON extraction")
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
        return text

    def _generate_sync(self, prompt: str, max_tokens: int, temperature: float, json_mode: bool = False):
        """Synchronous call to Gemini API via google-genai SDK."""
        config_kwargs = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "thinking_config": genai_types.ThinkingConfig(thinking_budget=0),
        }
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"

        return self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(**config_kwargs),
        )

    async def extract_constraints(
        self,
        natural_language_request: str
    ) -> TravelConstraints:
        if not self._client:
            raise RuntimeError("Gemini client not initialized. Check GEMINI_API_KEY.")

        estimated_tokens = self._tracker.estimate_request_cost(
            len(natural_language_request) + 2000,
            expected_response_length=1500
        ) if self._tracker else 3000

        if not self._check_token_budget(estimated_tokens):
            summary = self._tracker.get_usage_summary() if self._tracker else {}
            raise TokenBudgetExceeded(
                requested=estimated_tokens,
                remaining=summary.get("remaining", 0),
                limit=summary.get("daily_limit", 100000)
            )

        cache_key_prompt = f"constraints:{natural_language_request}"
        cached = self._check_cache(cache_key_prompt, self.model)
        if cached and isinstance(cached, TravelConstraints):
            print(f"Cache hit for: {natural_language_request[:50]}...")
            return cached
        print(f"Extracting constraints for: {natural_language_request}")

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
  * If user specifies a budget style without an exact number, set budget_tier to "budget", "moderate", or "luxury".
  * If neither amount nor tier is mentioned, set budget_total to null and budget_tier to null.
  * DO NOT guess or invent default budget or duration values if omitted.

TRIP TYPE DETECTION:
- ROAD TRIP countries (Iceland, Norway, New Zealand, Scotland, Ireland):
  Set is_road_trip=true. Generate 4-8 ROUTE STOPS.
- CITY TRIP destinations (Paris, Tokyo, NYC, Dubai):
  Set is_road_trip=false. Use 1-3 cities.
- MULTI-CITY countries (Japan, Italy, Spain):
  Set is_road_trip=false. Generate 2-4 key cities.
- For road trips: add "self-drive", "scenic routes", "nature" to preferences.
"""

        try:
            combined_prompt = f"{system_prompt}\n\nUser request: {natural_language_request}"

            response = await asyncio.to_thread(
                self._generate_sync, combined_prompt, self.max_tokens, self.temperature, True
            )

            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                self._record_usage(
                    getattr(response.usage_metadata, 'prompt_token_count', 0) or 0,
                    getattr(response.usage_metadata, 'candidates_token_count', 0) or 0,
                )

            content = self._extract_json(self._get_response_text(response))
            data = json.loads(content)
            constraints = TravelConstraints.model_validate(data)

            self._set_cache(cache_key_prompt, self.model, constraints)
            return constraints

        except TokenBudgetExceeded:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to extract constraints: {str(e)}")

    async def generate_with_schema(
        self,
        prompt: str,
        system_prompt: str,
        output_schema: Type[T],
        max_tokens: Optional[int] = None
    ) -> T:
        if not self._client:
            raise RuntimeError("Gemini client not initialized")

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

        cached = self._check_cache(prompt, self.model)
        if cached and isinstance(cached, output_schema):
            return cached

        try:
            combined_prompt = f"{system_prompt}\n\n{prompt}"

            response = await asyncio.to_thread(
                self._generate_sync, combined_prompt, max_tokens or self.max_tokens, self.temperature, True
            )

            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                self._record_usage(
                    getattr(response.usage_metadata, 'prompt_token_count', 0) or 0,
                    getattr(response.usage_metadata, 'candidates_token_count', 0) or 0,
                )

            content = self._extract_json(self._get_response_text(response))
            data = json.loads(content)
            result = output_schema.model_validate(data)

            self._set_cache(prompt, self.model, result)
            return result

        except Exception as e:
            raise RuntimeError(f"Generation failed: {str(e)}")

    async def chat_with_retry(
        self,
        messages: list,
        max_tokens: int = 900,
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
        max_retries: int = 3,
    ) -> str:
        """Chat completion with automatic retry — matches GroqClient interface."""
        if not self._client:
            raise RuntimeError("Gemini client not initialized")
        max_tokens = min(max_tokens, 2000)

        combined = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                combined.append(f"[System Instructions]\n{content}")
            else:
                combined.append(content)
        prompt_text = "\n\n".join(combined)

        json_mode = bool(response_format and response_format.get("type") == "json_object")

        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self._generate_sync,
                    prompt_text,
                    max_tokens,
                    temperature or self.temperature,
                    json_mode,
                )

                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    self._record_usage(
                        getattr(response.usage_metadata, 'prompt_token_count', 0) or 0,
                        getattr(response.usage_metadata, 'candidates_token_count', 0) or 0,
                    )

                text = self._get_response_text(response)
                if json_mode:
                    text = self._extract_json(text)
                return text

            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate" in err_str.lower() or "quota" in err_str.lower() or "503" in err_str:
                    wait = 5 * (attempt + 1)
                    print(f"Rate limited, waiting {wait}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait)
                    continue
                raise
        raise RuntimeError("Max retries exceeded for rate limit")

    def get_token_summary(self) -> Dict[str, Any]:
        if self._tracker:
            return self._tracker.get_usage_summary()
        return {"tracking_disabled": True}


_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
