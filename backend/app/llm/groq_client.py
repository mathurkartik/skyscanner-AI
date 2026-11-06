import logging
logger = logging.getLogger(__name__)
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
            logger.info("Cache hit for: %s...", natural_language_request[:50].encode("ascii", "replace").decode("ascii"))
            return cached
        logger.info("Extracting constraints for: %s", natural_language_request.encode("ascii", "replace").decode("ascii"))
        
        # Build structured extraction prompt
        system_prompt = """You are a travel planning assistant. Extract structured travel constraints from the user's request.
The user may write in English, Hindi, Hinglish (e.g. 'Mujhe 7 din ka Kerala trip plan karo'), or other languages. Extract all fields accurately regardless of language.

Respond with valid JSON matching this schema:
{
  "origin_city": "City or country departing from, or null if not mentioned (e.g. Cambodia, New York, London)",
  "destination_region": "Country or region name, or null if not mentioned",
  "cities": ["Stop1", "Stop2", ...],
  "start_date": "YYYY-MM-DD format if mentioned, or null",
  "duration_days": number or null,
  "budget_total": number or null,
  "budget_tier": "budget, moderate, luxury, or null",
  "currency": "3-letter code: USD, EUR, INR, GBP, JPY, THB, AUD, NZD, SEK, CAD, CHF",
  "group_size": number (default 1),
  "accessibility_needs": ["wheelchair", "mobility", "visual", "hearing"] or null,
  "preferences": ["what they want to experience"],
  "avoidances": ["what they want to avoid"],
  "hard_requirements": ["must-haves inferred from request"],
  "soft_preferences": ["nice-to-haves inferred"],
  "is_road_trip": boolean,
  "transport_segments": [
    {
      "from_city": "Origin or previous stop",
      "to_city": "Destination city",
      "recommended_mode": "flight | train | bus | drive | ferry",
      "reason": "Clear justification (e.g. 2h TGV high-speed rail, domestic railway connectivity, intercontinental flight)",
      "estimated_duration_hours": 2.5,
      "estimated_cost_usd": 45.0,
      "operator_name": "e.g. SNCF TGV, Shinkansen, Indian Railways, SBB, FlixBus, Turkish Airlines",
      "booking_url": "e.g. https://www.thetrainline.com/ or https://www.skyscanner.com/"
    }
  ]
}

CRITICAL EXTRACTION RULES (STRICT - DO NOT INVENT MISSING DATA):
- Origin: Extract departure origin if user states where they are traveling from (e.g., "trip from Cambodia", "flying from JFK", "departing London"). If not stated, set origin_city to null.
- Destination: Extract the primary destination/country/city. If user does NOT state where they want to go, set destination_region to null and cities to [].
- Start Date: Extract departure date in YYYY-MM-DD if mentioned (or first day of month if a month is mentioned, e.g. "December 2026" -> "2026-12-01"). If not mentioned, set to null.
- Duration: Extract duration in days: "weekend" = 2 days, "long weekend" = 3 days, "week" = 7 days, "fortnight" = 14 days, "N din" = N days. If user does NOT mention duration or days, set duration_days to null.
- Group Size: Extract number of travelers/friends/family (e.g. "6 friends" -> 6, "couple" or "for two" -> 2, "solo" -> 1). Default to 1 if not specified.
- Accessibility: Detect wheelchair, mobility, visual, or hearing accessibility requirements.
- Currency: 3-letter code: USD, EUR, INR, GBP, JPY, THB, AUD, NZD, SEK, CAD, CHF. Infer from symbols: ₹ or Rs or Lakh or L -> INR, € -> EUR, £ -> GBP, ¥ or yen -> JPY, ฿ or baht -> THB, kr or krona -> SEK, A$ -> AUD. Default to USD if no currency or symbol is mentioned.
- Multi-Modal Transport Mode Selection:
  * For long-distance (>800km without bullet rail) or overseas travel -> recommended_mode: "flight"
  * For domestic or intercity routes with reliable rail (e.g., Paris-Lyon, Tokyo-Kyoto, Zurich-Lucerne, Gandhinagar-Sholapur, Delhi-Agra, Rome-Florence) -> recommended_mode: "train"
  * For scenic driving routes, road trips, or outback areas -> recommended_mode: "drive"
  * For island hops or coastal water crossings -> recommended_mode: "ferry"
- Budget:
  * If a numeric budget is stated ($2000, 50000 INR, 10000$, 10L, 3.5 Lakh, etc.), extract the number into budget_total and the 3-letter currency into currency (e.g. 10L -> 1000000 INR).
  * If user specifies a budget style without an exact number (e.g., "cheap", "backpacking", "budget trip" -> "budget"; "moderate", "mid-range", "reasonable" -> "moderate"; "luxury", "5-star", "lavish" -> "luxury"), set budget_tier to "budget", "moderate", or "luxury".
  * If neither amount nor tier is mentioned, set budget_total to null and budget_tier to null.
  * DO NOT guess or invent default budget or duration values if omitted.

TRIP TYPE DETECTION:
- ROAD TRIP detection:
  If user mentions "road trip", "drive", "scenic drives", "self-drive", "car rental", "route", OR if destination is a classic road trip region (Iceland, Norway, Sweden, New Zealand, Scotland, Ireland, Croatia, Rajasthan, Portugal coast, South Africa Garden Route, Australia outback):
  Set is_road_trip=true. Generate 4-8 ROUTE STOPS (regions/towns along the route), NOT just the capital.
  Example Iceland: cities=["Reykjavik","Vik","Hofn","Egilsstadir","Akureyri","Snaefellsnes"]
  Example Norway: cities=["Oslo","Bergen","Geiranger","Alesund","Tromso"]
  Example Sweden: cities=["Stockholm","Tällberg","Gothenburg","Smögen","Malmö"]
  Example New Zealand: cities=["Auckland","Rotorua","Wellington","Queenstown","Milford Sound"]

- CITY TRIP destinations (Paris, Tokyo, NYC, Dubai, Singapore):
  Set is_road_trip=false. Use 1-3 cities as appropriate.

- MULTI-CITY countries (Japan, Italy, Spain, Russia):
  Set is_road_trip=false. Generate 2-4 key cities.
  Example Japan: cities=["Tokyo","Kyoto","Osaka"]
  Example Russia: cities=["Moscow","Saint Petersburg","Murmansk"]

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
            
            # Rule fallback for origin if missed by LLM
            if not data.get("origin_city"):
                import re
                m = re.search(r'\bfrom\s+([a-zA-Z\s]+?)(?:\s+to\b|\s+for\b|\s+in\b|$)', natural_language_request, re.IGNORECASE)
                if m:
                    candidate = m.group(1).strip()
                    if candidate and candidate.lower() not in ["here", "home", "airport"]:
                        data["origin_city"] = candidate

            # Sanitize empty strings in numeric fields before parsing
            data = self._sanitize_numeric_fields(data)

            # Safe numeric conversion for duration, group_size and budget
            if data.get("duration_days") is not None:
                try:
                    data["duration_days"] = int(data["duration_days"])
                except (ValueError, TypeError):
                    data["duration_days"] = None
            if data.get("group_size") is not None:
                try:
                    data["group_size"] = max(1, int(data["group_size"]))
                except (ValueError, TypeError):
                    data["group_size"] = 1
            if data.get("budget_total") is not None:
                try:
                    data["budget_total"] = float(data["budget_total"])
                except (ValueError, TypeError):
                    data["budget_total"] = None

            # Rule-based overrides for fields the LLM commonly misses
            data = self._apply_rule_overrides(data, natural_language_request)

            constraints = TravelConstraints.model_validate(data)
            
            # Cache result
            self._set_cache(cache_key_prompt, self.model, constraints)
            
            return constraints
            
        except TokenBudgetExceeded:
            raise
        except Exception as e:
            # Log error with context
            raise RuntimeError(f"Failed to extract constraints: {str(e)}")

    @staticmethod
    def _sanitize_numeric_fields(data: dict) -> dict:
        """Replace empty strings with None for fields that should be numeric,
        and sanitize nested transport_segments."""
        # Top-level numeric fields
        for key in ('duration_days', 'group_size', 'budget_total'):
            val = data.get(key)
            if isinstance(val, str) and val.strip() == '':
                data[key] = None

        # Nested transport_segments
        for seg in data.get('transport_segments', []):
            if isinstance(seg, dict):
                for num_key in ('estimated_duration_hours', 'estimated_cost_usd'):
                    val = seg.get(num_key)
                    if isinstance(val, str):
                        try:
                            seg[num_key] = float(val) if val.strip() else None
                        except ValueError:
                            seg[num_key] = None

        return data

    @staticmethod
    def _apply_rule_overrides(data: dict, raw_text: str) -> dict:
        """Deterministic post-LLM overrides for fields the model commonly misses."""
        import re
        text_lower = raw_text.lower()

        # --- Currency override ---
        # If the user explicitly wrote a currency symbol or keyword, trust that over the LLM
        currency_patterns = [
            (r'₹|(?:^|\s)rs\.?|\brupees?\b|\binr\b|\blakh\b|\blakhs\b|\b(\d+)\s*l\b', 'INR'),
            (r'€|(?:^|\s)eur\b|\beuros?\b', 'EUR'),
            (r'£|(?:^|\s)gbp\b|\bpounds?\b', 'GBP'),
            (r'¥|(?:^|\s)jpy\b|(?:^|\s)yen\b', 'JPY'),
            (r'฿|(?:^|\s)thb\b|(?:^|\s)baht\b', 'THB'),
            (r'(?:^|\s)a\$|(?:^|\s)aud\b', 'AUD'),
            (r'(?:^|\s)nz\$|(?:^|\s)nzd\b', 'NZD'),
            (r'(?:^|\s)sek\b|(?:^|\s)krona\b|(?:^|\s)kronor\b', 'SEK'),
            (r'(?:^|\s)cad\b|(?:^|\s)c\$', 'CAD'),
            (r'(?:^|\s)chf\b|(?:^|\s)francs?\b', 'CHF'),
        ]
        for pattern, code in currency_patterns:
            if re.search(pattern, text_lower):
                data['currency'] = code
                break

        # --- Budget extraction for currency-keyword amounts ---
        # Handles "300000 yen", "50000 baht", "2000 EUR", "₹10L", "10 lakh" where LLM missed the budget
        if not data.get('budget_total'):
            lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakhs?|lac|lacs?|\s*l)\b', text_lower)
            if lakh_match:
                try:
                    data['budget_total'] = float(lakh_match.group(1)) * 100000
                    if not data.get('currency'):
                        data['currency'] = 'INR'
                except ValueError:
                    pass

        if not data.get('budget_total'):
            budget_match = re.search(
                r'(\d[\d,]*(?:\.\d+)?)\s*(?:yen|jpy|baht|thb|eur|euros?|gbp|pounds?|usd|dollars?|inr|rupees?|aud|nzd|sek|cad|chf|francs?)',
                text_lower
            )
            if budget_match:
                try:
                    data['budget_total'] = float(budget_match.group(1).replace(',', ''))
                    if not data.get('currency'):
                        matched_str = budget_match.group(0).lower()
                        if any(k in matched_str for k in ['yen', 'jpy']): data['currency'] = 'JPY'
                        elif any(k in matched_str for k in ['baht', 'thb']): data['currency'] = 'THB'
                        elif any(k in matched_str for k in ['eur', 'euro']): data['currency'] = 'EUR'
                        elif any(k in matched_str for k in ['gbp', 'pound']): data['currency'] = 'GBP'
                        elif any(k in matched_str for k in ['inr', 'rupee']): data['currency'] = 'INR'
                        elif any(k in matched_str for k in ['aud']): data['currency'] = 'AUD'
                        elif any(k in matched_str for k in ['nzd']): data['currency'] = 'NZD'
                        elif any(k in matched_str for k in ['sek', 'krona', 'kronor']): data['currency'] = 'SEK'
                        elif any(k in matched_str for k in ['cad']): data['currency'] = 'CAD'
                        elif any(k in matched_str for k in ['chf', 'franc']): data['currency'] = 'CHF'
                except ValueError:
                    pass

        # Also handle "$2000", "€3000", "£1500", "₹50000", "¥300000"
        if not data.get('budget_total'):
            symbol_budget = re.search(r'[\$€£₹¥฿]\s*(\d[\d,]*(?:\.\d+)?)', raw_text)
            if symbol_budget:
                try:
                    data['budget_total'] = float(symbol_budget.group(1).replace(',', ''))
                except ValueError:
                    pass

        # --- Duration keyword override ---
        if not data.get('duration_days'):
            duration_keywords = {
                r'\bweekend\b(?!\s+(?:long|extended))': 2,
                r'\blong\s+weekend\b': 3,
                r'\bweek\b': 7,
                r'\bfortnight\b': 14,
            }
            for pattern, days in duration_keywords.items():
                if re.search(pattern, text_lower):
                    data['duration_days'] = days
                    break

            # "N din" (Hindi for days)
            din_match = re.search(r'(\d+)\s*din\b', text_lower)
            if din_match and not data.get('duration_days'):
                try:
                    data['duration_days'] = int(din_match.group(1))
                except (ValueError, TypeError):
                    pass

        # --- Group size override ---
        if not data.get('group_size') or data.get('group_size') == 1:
            group_patterns = [
                (r'(?:for|with)\s+(\d+)\s+(?:friends?|people|persons?|travelers?|travellers?|pax)', lambda m: int(m.group(1))),
                (r'(\d+)\s+(?:friends?|people|persons?|travelers?|travellers?)', lambda m: int(m.group(1))),
                (r'\b(?:couple|for\s+two|two\s+of\s+us)\b', lambda m: 2),
                (r'\bfamily\s+of\s+(\d+)\b', lambda m: int(m.group(1))),
                (r'\bsolo\b', lambda m: 1),
            ]
            for pattern, extractor in group_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    try:
                        data['group_size'] = extractor(match)
                    except (ValueError, TypeError):
                        pass
                    break

        # --- Accessibility override ---
        if not data.get('accessibility_needs'):
            accessibility_keywords = {
                'wheelchair': 'wheelchair',
                'mobility': 'mobility',
                'visual impair': 'visual',
                'blind': 'visual',
                'hearing impair': 'hearing',
                'deaf': 'hearing',
                'accessible': 'wheelchair',  # "accessible trip" implies wheelchair
            }
            found = []
            for keyword, need in accessibility_keywords.items():
                if keyword in text_lower and need not in found:
                    found.append(need)
            if found:
                data['accessibility_needs'] = found

        return data
    
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

    @property
    def semaphore(self) -> asyncio.Semaphore:
        if not hasattr(self, "_sem") or self._sem is None:
            self._sem = asyncio.Semaphore(2)
        return self._sem

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

        async with self.semaphore:
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
