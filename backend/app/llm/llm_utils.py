"""
Shared LLM Utilities for extraction, sanitization, and deterministic rule overrides.
Used by GroqClient, GeminiClient, and ResilientLLMClient to prevent code duplication (DRY).
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> str:
    """Extract JSON from LLM response that may contain markdown fences or preamble."""
    if not text:
        return "{}"
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        start = 1
        end = len(lines)
        for i in range(1, len(lines)):
            if lines[i].strip() == "```":
                end = i
                break
        cleaned = "\n".join(lines[start:end]).strip()
    
    brace = cleaned.find("{")
    bracket = cleaned.find("[")
    if brace == -1 and bracket == -1:
        return cleaned
    if brace == -1:
        start = bracket
    elif bracket == -1:
        start = brace
    else:
        start = min(brace, bracket)
    
    candidate = cleaned[start:]
    # If trailing characters follow JSON closing brace/bracket, trim
    rbrace = candidate.rfind("}")
    rbracket = candidate.rfind("]")
    end_idx = max(rbrace, rbracket)
    if end_idx != -1:
        candidate = candidate[:end_idx + 1]
    return candidate


def validate_llm_json(
    data: Any,
    required_keys: Optional[List[str]] = None,
    expected_type: type = dict,
    caller_name: str = "LLM"
) -> bool:
    """
    Validates parsed LLM JSON output against expected type and required keys (AG-017).
    Logs warnings when the structure deviates or expected keys are missing.
    """
    if not isinstance(data, expected_type):
        logger.warning(
            f"[{caller_name}] LLM output type mismatch: expected {expected_type.__name__}, got {type(data).__name__}"
        )
        return False

    if required_keys and isinstance(data, dict):
        missing = [k for k in required_keys if k not in data or data[k] is None]
        if missing:
            logger.warning(
                f"[{caller_name}] LLM output missing expected fields: {missing}. Available keys: {list(data.keys())}"
            )
            return False

    return True


def validate_item_fields(
    item: Any,
    required_keys: List[str],
    caller_name: str = "LLM"
) -> bool:
    """
    Validates a single item dictionary within a list of LLM-generated items (AG-017).
    Logs warnings when expected fields are missing.
    """
    if not isinstance(item, dict):
        logger.warning(f"[{caller_name}] Expected item dict, got {type(item).__name__}")
        return False
    missing = [k for k in required_keys if k not in item or item[k] is None]
    if missing:
        logger.warning(f"[{caller_name}] Item missing fields: {missing}. Present keys: {list(item.keys())}")
        return False
    return True


def sanitize_numeric_fields(data: dict) -> dict:
    """
    Replace empty strings with None for fields that should be numeric,
    and sanitize nested transport_segments.
    """
    if not isinstance(data, dict):
        return data

    for key in ("duration_days", "group_size", "budget_total"):
        val = data.get(key)
        if isinstance(val, str) and val.strip() == "":
            data[key] = None

    for seg in data.get("transport_segments", []):
        if isinstance(seg, dict):
            for num_key in ("estimated_duration_hours", "estimated_cost_usd"):
                val = seg.get(num_key)
                if isinstance(val, str):
                    try:
                        seg[num_key] = float(val) if val.strip() else None
                    except ValueError:
                        seg[num_key] = None

    return data


def apply_rule_overrides(data: dict, raw_text: str) -> dict:
    """
    Deterministic post-LLM overrides for fields models commonly miss:
    - Currency extraction (including INR, EUR, GBP, JPY, THB, AUD, NZD, SEK, CAD, CHF)
    - Comma-formatted budget extraction ($3,000, ₹10,00,000, €2,500)
    - Semantic road trip detection
    - Duration keywords (weekend, week, fortnight, Hindi 'din')
    - Group size and accessibility needs
    """
    if not isinstance(data, dict):
        return data

    text_lower = raw_text.lower()

    # 1. Currency override
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
        (r'\$|(?:^|\s)usd\b|\bdollars?\b', 'USD'),
    ]
    for pattern, code in currency_patterns:
        if re.search(pattern, text_lower):
            data['currency'] = code
            break

    # 2. Budget extraction for lakh / lac notation
    if not data.get('budget_total'):
        lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakhs?|lac|lacs?|\s*l)\b', text_lower)
        if lakh_match:
            try:
                data['budget_total'] = float(lakh_match.group(1)) * 100000.0
                if not data.get('currency'):
                    data['currency'] = 'INR'
            except ValueError:
                pass

    # 3. Budget extraction for comma-formatted or plain numbers with currency
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

    # 4. Budget symbol extraction: "$3,000", "€2,500", "£1,500", "₹50,000", "¥300,000"
    if not data.get('budget_total'):
        symbol_budget = re.search(r'[\$€£₹¥฿]\s*(\d[\d,]*(?:\.\d+)?)', raw_text)
        if symbol_budget:
            try:
                data['budget_total'] = float(symbol_budget.group(1).replace(',', ''))
            except ValueError:
                pass

    # 5. Semantic road trip detection (P1-4)
    road_trip_keywords = [
        "road trip", "roadtrip", "road-trip", "scenic drive", "scenic drives",
        "driving", "self-drive", "self drive", "car rental", "rental car",
        "coastal drive", "ring road", "drive around", "driving tour"
    ]
    classic_road_trip_destinations = [
        "iceland", "norway", "sweden", "scotland", "ireland", "new zealand",
        "croatia", "switzerland", "rajasthan", "south africa", "australia",
        "portugal", "namibia", "patagonia", "tasmania"
    ]
    if any(k in text_lower for k in road_trip_keywords):
        data['is_road_trip'] = True
        prefs = data.get('preferences') or []
        if 'road trip' not in [p.lower() for p in prefs]:
            prefs.append('road trip')
        data['preferences'] = prefs
    elif not data.get('is_road_trip'):
        dest_val = str(data.get('destination_region') or '').lower()
        if any(r in dest_val or r in text_lower for r in classic_road_trip_destinations):
            if any(k in text_lower for k in ["drive", "stops", "loop", "route", "circuit"]):
                data['is_road_trip'] = True

    # 6. Duration keyword override
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

        # Hindi 'din' e.g. "7 din"
        din_match = re.search(r'(\d+)\s*din\b', text_lower)
        if din_match and not data.get('duration_days'):
            try:
                data['duration_days'] = int(din_match.group(1))
            except (ValueError, TypeError):
                pass

    # 7. Group size override
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

    # 8. Accessibility needs override
    if not data.get('accessibility_needs'):
        accessibility_keywords = {
            'wheelchair': 'wheelchair',
            'mobility': 'mobility',
            'visual impair': 'visual',
            'blind': 'visual',
            'hearing impair': 'hearing',
            'deaf': 'hearing',
            'accessible': 'wheelchair',
        }
        found = []
        for keyword, need in accessibility_keywords.items():
            if keyword in text_lower and need not in found:
                found.append(need)
        if found:
            data['accessibility_needs'] = found

    return data
