# Competitor Gap Analysis: Exhaustive Bug Catalog
## Our Tool vs Claude Sonnet 5.5 / Gemini / ChatGPT

> **46 bugs cataloged** across 26 API tests + full frontend template audit  
> **Date**: 2026-11-06  
> **26 API tests**: Sweden 12d, Japan 7d, India/Italy/Thailand/Dubai/Iceland 5-10d, Singapore 1d, SE Asia 30d, Maldives, Georgia, Paris multi-city, Group Goa, Family Bali, Wheelchair Japan, NYC dates, Rajasthan train, Honeymoon Santorini, Road trip Munich, Weekend Pondicherry, Portugal verbose, Hindi Kerala  
> **Frontend audit**: itinerary-display.component.html (1021 lines), ai-travel-planner.component.ts, travel-planner.service.ts, review.py

---

## Executive Summary

Our tool has **structural advantages no competitor offers** — live Duffel API flights with booking deeplinks, per-day hotel inventory with guest ratings and swap suggestions, and structured multi-modal transport segments as machine-readable JSON. But the **content quality of the travel plan itself** — the actual advice a traveler reads — is significantly behind all three competitors.

**46 bugs found**: 12 P0 (showstoppers) | 18 P1 (competitive gaps) | 12 P2 (polish) | 4 P3 (nice-to-have)

Two meta-bugs cause 60% of frontend issues: the **Iceland Template** (6 bugs — hardcoded Iceland content shows on all trips) and **Currency Chaos** (10 bugs — 4 conflicting currency behaviors across frontend/backend).

**Overall scores**: Claude Sonnet 63/100 | Gemini 69/100 | ChatGPT 73/100 | **Our tool 52/100**

---

## Where We Win (Unique Differentiators)

### 1. Live bookable flights (Duffel API)
- Returned 5 real flight offers DEL→KRN with airline names, prices, stop counts, and booking deeplinks
- Competitors: estimated price ranges with no actionable booking link

### 2. Per-day hotel inventory with ratings
- Each of 12 days has 3 hotel options with name, nightly rate, guest rating (8.5-8.9), and swap suggestions
- 4 concrete cost-saving swaps: "Switch Icehotel → Scandic Kiruna, save ₹5,395"
- Competitors: "book a mid-range hotel" generically

### 3. Structured multi-modal transport
- 8 transport segments as JSON: `Stockholm→Gothenburg via train (SJ, 3h, $60)`
- Machine-readable, renderable in the Angular UI with booking links per mode
- Competitors: prose descriptions only

### 4. Interactive Angular UI
- Map with pins, day selector, flight/hotel cards, budget visualizer
- Not just a text response — a full application experience
- Competitors: text output only (Gemini adds Google Maps pins in their UI)

---

## Critical Bugs Found (7 Root Causes)

### Bug 1: Route Design — Generic City-Hopping Instead of Scenic Drive

**Symptom**: Cities extracted as `[Kiruna, Stockholm, Gothenburg, Malmö]` — the 4 biggest cities.  
**User asked for**: "love nature and scenic drives" → should produce Lake Siljan, Dalarna, Bohuslän coast, Vildmarksvägen.  
**All competitors**: Designed nature-first road routes through lesser-known scenic regions.

**Root cause**: `is_road_trip` was set to `false`. Sweden is NOT in the road trip countries list.

**File**: `backend/app/llm/groq_client.py` line 196 and `gemini_client.py` line 226  
```
ROAD TRIP countries (Iceland, Norway, New Zealand, Scotland, Ireland, Portugal coast, South Africa Garden Route, Australia outback)
```
Sweden is absent. The list is also incomplete — missing Switzerland, Scotland Highlands, Croatia coast, Japan countryside, etc.

**Deeper issue**: The road trip detection is a static country list in the prompt, not a semantic understanding. "Scenic drives" should trigger road trip mode regardless of country.

**Fix direction**:
- Add Sweden to the road trip countries list (quick fix)
- Better: add a rule — if user mentions "scenic drives", "road trip", "driving", "self-drive" in preferences, set `is_road_trip=true` regardless of country
- Even better: let the LLM decide based on context, not a hardcoded list

---

### Bug 2: Budget is ₹1.96L on a ₹10L Trip (80% Under-Counted)

**Symptom**: Grand total ₹195,912. Food ₹9,000 for 12 days (₹750/day in Sweden!). Activities ₹6,000 total.  
**All competitors**: Budgeted ₹7-9.5L realistically.

**Root cause**: The LLM budget analysis **crashes** with a Pydantic validation error:
```
LLM budget analysis failed: 1 validation error for BudgetCategory
category
  Input should be 'stay', 'transport', 'food', 'activities' or 'buffer'
  input_value='intercity transport'
```

The LLM returned `"intercity transport"` as a category name. The schema accepts only `Literal["stay", "transport", "food", "activities", "buffer"]`.

**File**: `backend/app/agents/budget.py` line 177-235, `backend/app/models/schemas.py` line 338  
The system prompt says `"category": "stay|food|transport|activities"` but doesn't enforce this strictly enough for the LLM.

When the LLM analysis fails, it falls back to `_fallback_analyze()` which produces bare-minimum estimates disconnected from reality.

**Fix direction**:
- Normalize LLM category values before Pydantic validation: map "intercity transport", "flights", "trains" → "transport"
- Add `"buffer"` to the prompt's category list
- Make the prompt more explicit: "category MUST be exactly one of: stay, transport, food, activities, buffer"

---

### Bug 3: Day Narratives Drop Out After Day 7

**Symptom**: Days 1-7 have mood, highlight, and rich narrative. Days 8-12 show `None` for all three.  
**Japan 7-day test**: 0/7 missing (all fit within limit).

**Root cause**: `max_tokens=800` for the narrative enrichment LLM call.

**File**: `backend/app/agents/orchestrator.py` line 1299  
```python
max_tokens=800  # Too low for 12+ days
```

Each day needs ~80-100 tokens (mood + highlight + 2-sentence narrative). 12 days × 90 = 1,080 tokens minimum + JSON overhead. 800 tokens cuts off around day 7-8.

**Fix direction**:
- Scale `max_tokens` dynamically: `min(max(duration_days * 120, 800), 3000)`
- Or split into batches of 6 days per call

---

### Bug 4: Map Pin Coordinates Default to Iceland

**Symptom**: All 4 overnight hotel pins share coordinates `(64.1466, -21.9426)` — Reykjavik, Iceland.  
**Japan test**: 2/11 pins had Iceland coords (the hotel pins).  
**Attraction pins**: Correct coordinates from Google Places API.

**Root cause**: `_COORDS_CACHE` is an empty dict that is never populated. `_lookup_city_coords()` always returns `None`. The fallback is hardcoded Iceland.

**File**: `backend/app/agents/orchestrator.py` lines 30-39
```python
_COORDS_CACHE: Dict[str, Tuple[float, float]] = {}  # Always empty

def _lookup_city_coords(name: str) -> Optional[Tuple[float, float]]:
    name_clean = name.lower().strip()
    if name_clean in _COORDS_CACHE:
        return _COORDS_CACHE[name_clean]
    return None  # Always returns None
```

Line 1141:
```python
coords = _lookup_city_coords(day.city) or (64.1466, -21.9426)  # Iceland fallback
```

This is a leftover from when the hardcoded `CITY_COORDINATES` dict was deleted but not replaced with dynamic geocoding.

**Fix direction**:
- Use coordinates from the day's places (Google Places already has lat/lng for attractions in that city)
- Or populate `_COORDS_CACHE` from transport segments / hotel data
- Or use a geocoding API call (Google Geocoding is already in the API key set)
- Remove the Iceland fallback entirely — better to omit a pin than show it in the wrong ocean

---

### Bug 5: Flight Prices in Wrong Currency (AUD Instead of INR)

**Symptom**: Flights returned as `427.67 AUD` despite user specifying ₹ (INR) budget.

**Root cause**: The Duffel API returns prices in the airline's native currency. The `currency` parameter is passed to `_query_duffel_api()` but **never included in the API request** — Duffel doesn't support a currency param in offer requests.

**File**: `backend/app/tools/flight_client.py` lines 307-313  
The payload has no currency field:
```python
payload = {"data": {"slices": slices, "passengers": [...], "cabin_class": ...}}
```

The budget calibration in `budget.py:76` assumes USD:
```python
flight_cost_curr = round(cheapest_flight.price * fx_usd_to_curr, 2)
```
But if the flight is in AUD, this math is wrong.

**Fix direction**:
- After receiving Duffel offers, convert from `offer_currency` to the user's target currency using exchange rates
- Use a hardcoded FX lookup or a free API (exchangerate.host is free)
- At minimum: don't display raw Duffel currency to the user — convert or label clearly

---

### Bug 6: Zero Practical Travel Information

**What competitors provided** (all three):
- Schengen visa requirements for Indian passport holders (€90 fee, VFS process, 15-day processing)
- International Driving Permit requirement for car rental
- Fuel costs (SEK 17-20/litre) and toll rules
- Seasonal road closures (Stekenjokk opens June 6)
- Midsummer timing and accommodation booking lead times
- Right of public access (allemansrätten)
- Moose warnings at dawn/dusk
- Currency conversion rates (SEK to INR)
- Travel insurance recommendations
- Automatic vs manual car transmission defaults in Europe

**What we provide**: Nothing. No visa, no driving tips, no seasonal warnings, no currency context.

**Root cause**: No schema field, agent, or LLM prompt exists for practical travel information.

**File**: `backend/app/models/schemas.py` — `FinalItinerary` has `best_time_to_visit` and `what_not_to_do` but nothing for visa/documents, driving requirements, local customs, or seasonal logistics.

**Fix direction**:
- Add a `practical_info` section to the schema: visa requirements, driving licence/IDP, currency tips, seasonal warnings, booking lead times, local customs
- Generate via a single LLM call in `_generate_insights()` or a dedicated prompt
- The LLM already knows all of this — it just needs to be asked

---

### Bug 7: Constraint Extraction Drops "$3,000 Budget" Format

**Symptom**: "Plan a 7-day Japan trip: Tokyo + Kyoto, $3,000 budget" → 3-pillar validator rejects for missing budget.  
Rephrased as "budget is 3000 USD" → extracts correctly.

**Root cause**: The `$3,000` format with comma separator wasn't parsed by the LLM. The constraint extraction prompt's budget examples don't include comma-separated numbers.

**File**: `backend/app/llm/groq_client.py` line 190 and `gemini_client.py` equivalent  
The prompt says: `"$2000, 50000 INR, 10000$"` — no comma-separated examples like `$3,000`.

**Fix direction**:
- Add comma-formatted examples to the prompt: `"$3,000"`, `"₹10,00,000"`, `"€2,500"`
- Or add a pre-processing step that strips commas from budget numbers before LLM extraction

---

## Non-Bug Gaps (Feature Parity Issues)

### 1. No seasonality awareness
All competitors discussed best months, midnight sun, northern lights, and recommended specific travel windows (Aug-Sept 2027). Our `best_time_to_visit` field exists but was generic in the output. The insights prompt asks for it but the response was thin.

### 2. No follow-up question
All competitors ended with a clarifying question: "What month?", "How many travelers?", "Summer or winter?". Our tool returns a final result with no conversation loop.

### 3. No driving distances between stops
Competitors showed per-segment kilometers (e.g., "Stockholm → Dalarna ~300km"). Our transport segments show duration but not distance.

### 4. No car rental results
Despite having a `car_estimates` field and `car_rental_client.py`, the Sweden output returned 0 car options. The Japan test also returned 0. The car rental pipeline may only trigger when `is_road_trip=true`.

### 5. Hotel pipeline returns 0 for top-level hotel_options
Both tests returned `hotel_options: []` at the top level, though per-day `hotel_options` had 3 each. The top-level list may not be populated from the per-day data.

### 6. Cost saving tips empty
The Sweden output had 0 `cost_saving_tips`. The structured `CostSavingTip` objects aren't generated for non-Iceland/Japan destinations.

---

## Competitor Strengths to Learn From

### Claude Sonnet 5.5 (Score: 63)
**Standout**: Practical information depth — visa fees with VFS link, fuel costs per litre with carbon tax expiry date, one-way rental fee ranges, IDP requirements, midsummer timing. Also cited 6 real URLs for verification.
**Weakness**: No visual map, no bookable actions.

### Gemini (Score: 69)
**Standout**: Two-phase trip design (Arctic flight + southern road loop) was creative. Beautiful Google Maps integration with clickable pins and place cards with ratings. Phase-based narrative structure was compelling.
**Weakness**: Budget breakdown was less itemized. Fewer practical details than Claude.

### ChatGPT (Score: 73)
**Standout**: Discovered Vildmarksvägen (Sweden's highest paved road) — a unique off-the-beaten-path choice none of the others found. Provided seasonal road closure dates with source links. Embedded images for each region. Most detailed budget table. Fulufjället National Park with specific waterfall trail distance (4km return).
**Weakness**: Slightly long (could be more concise). Fewer follow-up action items.

---

## Priority Fix Order

| Priority | Bug | Impact | Effort | Dependencies |
|----------|-----|--------|--------|-------------|
| **P0** | #2 Budget category crash | Budget shows 20% of reality | 30 min | None |
| **P0** | #4 Map pins = Iceland | Map is completely wrong | 1 hour | None |
| **P0** | #5 Currency mismatch | Prices meaningless to user | 1 hour | None |
| **P1** | #1 Route design | Plan quality vs competitors | 2 hours | None |
| **P1** | #3 Narrative truncation | Last days look broken | 15 min | None |
| **P1** | #6 Practical info | Major gap vs competitors | 2 hours | Schema change |
| **P2** | #7 Budget format parsing | Some prompts rejected | 30 min | None |
| **P2** | No car rental results | Missing for road trips | 1 hour | Bug #1 |
| **P2** | No seasonality | Plan lacks context | 30 min | Part of #6 |
| **P3** | Top-level hotel_options empty | UI may not render | 30 min | None |
| **P3** | No driving distances | Less useful than competitors | 30 min | Schema change |
| **P3** | Cost saving tips empty | Missing value-add | 30 min | None |

**Total estimated effort**: ~10 hours for P0+P1 fixes.

---

---

## Cross-Prompt Test Matrix (6 Tests)

| # | Prompt | Result | Time |
|---|--------|--------|------|
| 1 | Sweden 12-day ₹10L scenic drives | OK but low quality | 55s |
| 2 | Japan 7-day $3000 temples & food | OK (budget rejected with "$3,000" format) | 35s |
| 3 | India 6-day Mumbai→Rajasthan ₹50k | OK | 31s |
| 4 | Italy 10-day Rome/Florence/Amalfi €2500 | OK | 85s |
| 5 | Thailand 5-day backpacker $500 | OK | 42s |
| 6 | Dubai 4-day luxury £5000 | OK but wrong hotel tier | 23s |
| 7 | Iceland 8-day Ring Road ₹3L | **TOTAL FAILURE** | 3s |
| 8 | Vague "somewhere warm $2000" | Correctly rejected (missing destination) | 2s |

### Consolidated Bug Occurrence Table

| Bug | Sweden | Japan | India | Italy | Thailand | Dubai | Iceland |
|-----|--------|-------|-------|-------|----------|-------|---------|
| Budget category crash | YES ("intercity transport") | no | YES ("intercity") | no | no | no | n/a |
| Budget wildly wrong | YES (20% of budget) | YES (54%) | YES (240% over) | YES (80%) | YES (245% over) | YES (70%) | n/a |
| Iceland map pin fallback | 4/21 pins | 2/11 | 3/16 | 3/16 | 2/11 | 1/6 | n/a |
| Flight currency wrong | AUD | AUD | AUD | AUD | AUD | AUD | n/a |
| Missing narratives | 5/12 | 0/7 | 0/6 | 2/10 | 0/5 | 0/4 | n/a |
| No practical info | YES | YES | YES | YES | YES | YES | n/a |
| Top-level hotels empty | YES | YES | YES | YES | YES | YES | n/a |
| Car estimates empty | YES | YES | YES | YES | YES | YES | n/a |
| Cost saving tips empty | YES | YES | YES | YES | YES | YES | n/a |

### New Bugs Found in Extended Testing

---

### Bug 8: Gemini Model Deprecated — `gemini-2.5-flash` Returns 404

**Symptom**: Iceland test cascade-failed. Gemini returned:
```
404 NOT_FOUND: This model models/gemini-2.5-flash is no longer available to new users.
Please update your code to use models/gemini-3.8-flash.
```

**File**: `backend/app/config.py` line 50
```python
gemini_model: str = "gemini-2.5-flash"  # Deprecated
```

**Fix**: Change default to `gemini-3.8-flash`. Also update `.env` and `.env.example`.

---

### Bug 9: Gemini API Key 1 is Invalid / Expired

**Symptom**: `401 UNAUTHENTICATED — API key not valid`

**File**: `backend/.env` — `GEMINI_API_KEY` value is stale.

**Fix**: Regenerate from ai.google.dev. This is a configuration issue, not a code bug.

---

### Bug 10: Duplicate City Rejects Ring Road Itineraries

**Symptom**: Iceland Ring Road returns `cities: ['Reykjavik', ..., 'Vik', 'Reykjavik']` — the LLM puts Reykjavik as both start and end. Pydantic validator at `schemas.py:118` raises `ValueError: Duplicate city: Reykjavik`.

**Root cause**: Ring Road / circular routes naturally start and end in the same city. The validator is too strict.

**File**: `backend/app/models/schemas.py` lines 113-120
```python
@field_validator("cities")
def validate_no_duplicate_cities(cls, v):
    seen = set()
    for city in v:
        city_lower = city.lower().strip()
        if city_lower in seen:
            raise ValueError(f"Duplicate city: {city}")
        seen.add(city_lower)
```

**Fix**: Deduplicate silently instead of raising:
```python
@field_validator("cities")
def deduplicate_cities(cls, v):
    seen = set()
    result = []
    for city in v:
        if city.lower().strip() not in seen:
            seen.add(city.lower().strip())
            result.append(city)
    return result
```

---

### Bug 11: Hotel Tier Ignores Budget/Luxury Preference

**Symptom**: User asked for "luxury, 5-star hotels, £5000 budget" in Dubai. Got:
- Rove Downtown Dubai ($140/night) — budget brand
- Premier Inn Dubai Al Jaddaf ($140/night) — budget chain

These are 3-star budget hotels. A luxury traveler expects Burj Al Arab, Atlantis, or at minimum a Marriott/Hilton.

**Root cause**: The LLM hotel generation prompt doesn't receive the user's `budget_tier` or `budget_total` as context. It generates "popular" hotels without tier awareness.

**File**: `backend/app/tools/hotel_client.py` — the `_generate_llm_hotels()` method needs the budget tier passed through.

**Fix**: Pass `budget_tier` and `price_range` to the hotel generation prompt so the LLM can suggest tier-appropriate properties.

---

### Bug 12: Budget Math Consistently Wrong Across All Tests

Detailed budget accuracy across all 6 successful tests:

| Test | User Budget | Our Total | Ratio | Within? | Issue |
|------|------------|-----------|-------|---------|-------|
| Sweden 12d | ₹10,00,000 | ₹1,95,913 | 20% | True (wrong) | Food ₹9k for 12d in Sweden |
| Japan 7d | $3,000 | $1,609 | 54% | True (wrong) | Missing half the costs |
| India 6d | ₹50,000 | ₹1,19,904 | 240% | **False** | Hotels alone ₹1.05L on ₹50k budget |
| Italy 10d | €2,500 | €1,996 | 80% | True | Closest, but food €300 for 10d in Italy |
| Thailand 5d | $500 | $1,227 | 245% | **False** | Hotels $945 on $500 total budget |
| Dubai 4d | £5,000 | £3,517 | 70% | True | Activities £1,500 but hotel £420 total |

**Pattern**: The budget rollup is either massively under-counting (Sweden, Japan) or massively over-counting (India, Thailand) — it never matches reality. The LLM budget analysis crashes with the category validation error (Bug 2), and the fallback `_calibrate_with_real_data()` just uses raw hotel API prices without checking if they fit the budget.

**India bug**: Hotels totaled ₹1,04,580 on a ₹50,000 **total** budget. The calibration replaced the budget agent's estimate with live hotel prices without checking if those exceed the entire trip budget.

**Thailand bug**: Same issue — $945 in hotels on a $500 total budget. The hotel engine ignores budget constraints entirely.

**Fix direction**: After calibration, if `grand_total > budget_total`, the budget agent should:
1. Select cheaper hotel options (use the swap engine)
2. Or flag clearly that the budget is insufficient for this destination

---

### Bug 13: All Flights Return AUD Regardless of Requested Currency

Every single test returned flights priced in AUD (Australian Dollars), even for:
- India domestic flights (should be INR)
- Delhi→Rome (should be EUR or INR)
- London→Dubai (should be GBP)

**Root cause**: The Duffel API test key (sandbox mode) may be set to an Australian account/merchant, which returns all prices in AUD. This is a Duffel configuration issue — the API key's currency is AUD.

**Fix**: Either:
- Set the Duffel account currency to USD (most universal)
- Add a post-processing currency conversion step using the user's target currency
- Display "prices shown in AUD" disclaimer if conversion isn't available

---

### Bug 14: Groq Daily Quota Hit on Every Multi-Test Session

**Symptom**: Every test after the first one hits `"tokens per day"` limit:
```
Daily quota hit on openai/gpt-oss-120b; using openai/gpt-oss-20b for Xs
```

The 200k TPD free tier is exhausted after 1-2 plans. The fallback to `gpt-oss-20b` works but is lower quality.

**Impact**: In production on Render, if multiple users hit the tool in a day, every user after the first 1-2 gets degraded quality from the fallback model. This compounds all the other quality issues.

**Fix**: This is the original reason for dual-provider (Gemini primary). Fix Bugs 8+9 (Gemini model + key) to restore the high-throughput primary provider.

---

## Updated Priority Matrix (All 14 Bugs)

| Priority | Bug | Impact | Effort |
|----------|-----|--------|--------|
| **P0** | #8 Gemini model deprecated | Failover chain broken | 5 min (config change) |
| **P0** | #9 Gemini API key expired | Same | 5 min (regenerate key) |
| **P0** | #10 Duplicate city crash | Iceland/ring routes fail completely | 10 min |
| **P0** | #2 Budget category crash | Budget shows nonsense numbers | 30 min |
| **P0** | #4 Map pins = Iceland | Map is completely wrong | 1 hour |
| **P1** | #13 Flights always AUD | Prices meaningless in user's currency | 1 hour |
| **P1** | #12 Budget math wrong everywhere | Core value prop broken | 2 hours |
| **P1** | #11 Hotels ignore budget tier | Luxury user gets Premier Inn | 1 hour |
| **P1** | #1 Route design (scenic drives) | Plan quality vs competitors | 2 hours |
| **P1** | #3 Narrative truncation (>7 days) | Last days look broken | 15 min |
| **P1** | #6 No practical info | Major gap vs all competitors | 2 hours |
| **P2** | #14 Groq quota hit fast | Degraded quality after 1-2 plans | Fixed by #8+#9 |
| **P2** | #7 "$3,000" budget not parsed | Some prompts rejected | 30 min |
| **P2** | #5 Flight currency not converted | Display issue | 1 hour |

**Critical path**: Fix #8 + #9 first (10 min total) to restore Gemini as primary provider. This unblocks higher quality and fixes #14 automatically. Then #10 + #2 (40 min) to stop outright crashes. Then #4 + #12 + #11 (4 hours) for data correctness.

**Total**: ~12 hours for all P0+P1 fixes.

---

## Live UX Testing (Deployed App)

> **Tested**: https://skyscanner-ai-beige.vercel.app → "Plan with AI"  
> **Prompt**: "Plan a 12-day Sweden trip, 10 lakh INR budget, love nature and scenic drives"  
> **Pipeline time**: ~50 seconds, all 5 agents completed successfully

### What Works Well (UX Wins)

1. **Multi-agent pipeline progress bar** — Orchestrator → Destination → Logistics → Budget → Review with DONE/RUNNING states. Builds user trust during the 50s wait.
2. **Transit cards with dual currency** — Stockholm→Gothenburg High-Speed Rail $45 ≈₹3,735 with SJ Swedish Rail operator and "Book on Trainline" CTA. Excellent actionable format.
3. **Hotel comparison cards** — 3 options per city with rating, nightly rate, amenities, and deep links to Booking.com/Agoda/MakeMyTrip/Google. [Recommended] and [Great Value] tags.
4. **Google Places verified sights** — Live POI API badge, star ratings, review counts, photos. Adds real credibility.
5. **Strategic Routing Rationale** — Natural language explanation of why the route was designed this way. No competitor does this.
6. **Alternative trip suggestions** — "Tokyo & Kyoto (10 Days) Est. ₹2,90,000" | "Sikkim Monasteries (8 Days) Est. ₹1,15,000" — good for users who might pivot.
7. **Budget optimization tips** — "Book Flights 6-8 Weeks in Advance" with Skyscanner pricing data cited. Smart branding integration.
8. **Driving route alerts** — Fuel stops, bridge alerts, sunlight hours (07:30-18:45). Unique feature no competitor has.
9. **Day tabs with theme names** — "Coastal Wonder", "Freedom" — adds editorial character to the itinerary.
10. **Suggestion chips** — "Iceland Ring Road", "Tokyo & Kyoto", "Swiss Alps by Train" — reduces cold-start friction.

### Critical UX Bugs Found (New — Frontend/Display Layer)

---

### Bug 15: "Duffel Airways" — Sandbox Airline Shown to Real Users

**Symptom**: Live Flight Matches section shows "Duffel Airways [Recommended] ₹34,937 — 8.2 hrs, Direct Flight, 1 checked bag inc." as the top recommended flight.

**Impact**: "Duffel Airways" is a test airline from the Duffel API sandbox. It doesn't exist. Showing it as the recommended flight option destroys credibility — any user who Googles "Duffel Airways" will realize this is fake data.

**Root cause**: The app is running in Duffel sandbox mode, which returns test airlines alongside real ones. The sandbox test data isn't filtered out before display.

**Fix direction**:
- Filter out airlines where `airline.name == "Duffel Airways"` or flag sandbox results
- Or switch to Duffel production API if available
- At minimum: don't auto-recommend sandbox results

---

### Bug 16: Budget Summary Shows USD Amounts with ₹ Symbol

**Symptom**: Trip Spend Matrix displays:
- Stays (10 nights): **₹1,752** (66% of total)
- Transport & Car: **₹421**
- Food & Fuel: **₹280**
- Activities & Parks: **₹220**

₹1,752 for 10 nights in Sweden = ₹175/night ≈ $2.10/night. These are USD values being displayed with an ₹ prefix — no actual currency conversion happened.

**Impact**: The budget section — the core value prop for budget-conscious Indian travelers — shows numbers that are obviously nonsensical. Any user will immediately distrust the entire tool.

**Root cause**: The budget agent produces values in USD (from LLM), the `_calibrate_with_real_data()` in `budget.py:70` applies a simple FX multiplier only to flight and hotel actuals, but the LLM-generated food/activities/transport values stay in their original USD amounts with the ₹ symbol prepended in the UI.

**Linked to**: Bug #5 (currency mismatch), Bug #12 (budget math wrong)

---

### Bug 17: Route Breadcrumb Shows Every Day as Separate City Entry

**Symptom**: The city flow at the top reads: Kiruna → Kiruna → Stockholm → Stockholm → Stockholm → Stockholm → Gothenburg → Gothenburg → Gothenburg → Malmö → Malmö

**Impact**: Looks broken and confusing. A 4-city trip appears as 12 city entries.

**Root cause**: The frontend iterates over `days` and renders each day's `city` as a breadcrumb node. It should deduplicate consecutive cities into a single node showing the stay duration.

**Fix direction**:
- Group consecutive days with the same city: "Kiruna (2 days) → Stockholm (4 days) → Gothenburg (3 days) → Malmö (2 days)"
- This is a frontend-only fix in the Angular component

---

### Bug 18: Iceland Driving Warnings Applied to Malmö, Sweden

**Symptom**: Day 11 in Malmö shows: "Bridge Alert: Single-lane bridges along glacial sands"

**Impact**: Malmö is Sweden's third-largest city — it has multi-lane highways, not single-lane bridges over glacial sands. This is Iceland Ring Road content leaking into a Sweden itinerary via the template.

**Root cause**: The driving route alerts are likely generated from a template or static data originally written for Iceland. When the system was made dynamic, the alert content wasn't made destination-aware.

**Fix direction**:
- Make driving alerts LLM-generated based on the actual route/city, not templated
- Or remove alerts entirely if they can't be made accurate

---

### Bug 19: "Open 24 hrs" on Museums and Visitor Centres

**Symptom**: Google Places sights cards show "Open 24 hrs · Iconic Sight" for Kin Museum and LKAB Visitor Centre.

**Impact**: Minor but damages credibility — museums don't open 24 hours. This is Google Places API data being used without validation.

**Root cause**: The `opening_hours` field from Google Places API may return "24 hours" for places with irregular hours or missing data. The frontend displays it verbatim.

**Fix direction**: If `opening_hours` is "24 hours" or empty, show "Check hours" or hide the field instead of displaying "Open 24 hrs"

---

### Bug 20: No Day Narrative for Days 8-12 in the UI

**Symptom**: Days 1-7 show an italic narrative paragraph (e.g., *"Morning light filters through the wooden arches of Kiruna Kyrka..."*). Days 8-12 show only the activity timetable with no narrative.

**Impact**: The later days of the trip feel less curated and lower-quality. The contrast with the rich early days makes it obvious something went wrong.

**Root cause**: Confirmed — same as Bug #3 (`max_tokens=800` in `orchestrator.py:1299`). The token limit truncates narratives for trips >7 days.

---

### Summary Tab Appears Non-Functional

**Symptom**: Clicking "SUMMARY - All 11 Days Table" tab shows Day 11 content instead of a summary view.

**Impact**: Minor — the summary feature may not be fully implemented yet. Also says "11 Days" for a 12-day trip.

---

## Updated UX Scorecard: Our Tool vs Competitors

| Dimension | Our Tool | Claude | Gemini | ChatGPT |
|-----------|----------|--------|--------|---------|
| **Bookable flights** | Real Duffel data (but sandbox airline shown) | None | None | None |
| **Hotel cards** | 3 per city with booking links | None | None | None |
| **Transit segments** | Actionable with operator + booking CTA | Text only | Text only | Text only |
| **Map quality** | 21 pins but hotels at Iceland coords | None | Google Maps integration | None |
| **Budget accuracy** | 20-245% off, wrong currency display | No budget | Rough estimate | Detailed table |
| **Day content** | Rich for days 1-7, empty for 8-12 | Consistent all days | Consistent | Consistent |
| **Practical info** | None | Visa, IDP, fuel, customs | Moderate | Extensive |
| **Route design** | 4 big cities | Scenic loops | Two-phase creative | Off-beaten-path |
| **Interactive UI** | Full app with tabs, cards, filters | Text | Text + Maps | Text + images |
| **Trust signals** | Sandbox airlines, Iceland coords hurt trust | URLs cited | Google reviews | Source links |

**Key insight**: Our tool has the **best structural bones** (real data, booking links, interactive UI) but the **worst data accuracy** (wrong coordinates, wrong currency, fake airlines, broken budgets). Fixing the data layer would leapfrog all three competitors because none of them can offer bookable, real-time results.

---

## Revised Priority Matrix (All 20 Issues)

| Priority | Bug | Impact | Effort |
|----------|-----|--------|--------|
| **P0** | #8 Gemini model deprecated | Failover chain broken | 5 min |
| **P0** | #9 Gemini API key expired | Same | 5 min |
| **P0** | #10 Duplicate city crash | Ring routes fail completely | 10 min |
| **P0** | #15 "Duffel Airways" shown | Trust-destroying fake airline | 15 min |
| **P0** | #2 Budget category crash | Budget shows nonsense | 30 min |
| **P0** | #4 Map pins = Iceland | Map is completely wrong | 1 hour |
| **P0** | #16 ₹ on USD amounts | Budget numbers nonsensical | 30 min (part of #5) |
| **P1** | #13 Flights always AUD | Prices meaningless | 1 hour |
| **P1** | #12 Budget math wrong everywhere | Core value prop broken | 2 hours |
| **P1** | #11 Hotels ignore budget tier | Luxury user gets Premier Inn | 1 hour |
| **P1** | #1 Route design (scenic drives) | Plan quality vs competitors | 2 hours |
| **P1** | #3/#20 Narrative truncation | Last days look empty | 15 min |
| **P1** | #6 No practical info | Major gap vs all competitors | 2 hours |
| **P1** | #17 City breadcrumb duplication | Looks broken to users | 30 min (frontend) |
| **P1** | #18 Iceland alerts on Sweden | Content accuracy | 30 min |
| **P2** | #14 Groq quota hit fast | Degraded after 1-2 plans | Fixed by #8+#9 |
| **P2** | #7 "$3,000" budget not parsed | Some prompts rejected | 30 min |
| **P2** | #19 "Open 24 hrs" on museums | Minor trust issue | 15 min (frontend) |
| **P3** | Summary tab broken | Missing feature | 1 hour (frontend) |
| **P3** | Top-level hotel_options empty | Data gap | 30 min |

**Updated critical path**: #8+#9 (10 min) → #10+#15 (25 min) → #2+#16 (1 hour) → #4 (1 hour) = **P0 fixes in ~2.5 hours**. Then P1 in ~8 hours.

**Total**: ~14 hours for all P0+P1 fixes.

---

## Edge Case Testing (8 Stress Tests)

> **Method**: Direct API calls to https://skyscanner-ai.onrender.com/api/plan  
> **Date**: 2026-11-06

### Edge Case Results Matrix

| # | Test Case | Result | Time | Key Finding |
|---|-----------|--------|------|-------------|
| 1 | 1-day Singapore $500 | OK | 43.8s | Works but still has Iceland pin (1/6), AUD flights, Duffel Airways |
| 2 | 30-day SE Asia backpacking $3000 | OK | 151s | 21/30 narratives missing, 6 Iceland pins, multi-country decomposition worked |
| 3 | "Luxury 5-star Maldives" $500 | OK | 65.8s | No contradiction flagged, 14/14 narratives missing, budget_total null |
| 4 | "7 days Paris, art and food" (no budget) | **REJECTED** | 30s | Missing budget — correct validation but too strict vs competitors |
| 5 | "Georgia hiking and wine" $2000 | OK | 125.9s | Correctly resolved as country (Tbilisi, Mestia, Batumi), not US state |
| 6 | "tropical beach snorkeling" $1500 | **REJECTED** | 13s | Missing destination — should suggest specific places |
| 7 | "Paris and London and Amsterdam" €3000 | **REJECTED** | 1.2s | Missing destination — multi-city cross-country trips unsupported |
| 8 | ₹50L Switzerland luxury | OK | 1.1s | Suspiciously fast (stub?), 7/7 narratives missing, only 5 pins |

### New Bugs Found in Edge Case Testing

---

### Bug 21: Multi-City Cross-Country Prompts Rejected as "No Destination"

**Symptom**: "Paris and London and Amsterdam, 9 days, budget 3000 EUR, from Delhi" → HTTP 400 "Please provide the missing details: Destination"

**Impact**: This is a common travel pattern — European multi-city trips. Every competitor handles this naturally. Our tool can't plan any trip spanning multiple countries unless the user names a single region.

**Root cause**: Two layers fail:
1. **LLM extraction** (`groq_client.py:152`): `destination_region` expects "Country or region name" — three cities across France/UK/Netherlands doesn't map to one country
2. **Stub regex** (`routes.py:179`): `r'(?:trip\s+to|...|in|of)\s+([A-Z][a-zA-Z]+...)'` captures only the first capitalized word after a preposition — "Paris and London" has no preposition before "Paris"
3. **3-pillar validator**: When `destination_region` is null, it rejects immediately

**Fix direction**:
- If LLM returns `destination_region = null` but `cities` is non-empty, use the first city's country as destination_region
- Or: accept trips where cities span multiple countries → set `destination_region = "Europe"` or `"Multi-country"`
- The orchestrator already handles multi-city trips internally — the validation gate is blocking valid inputs

---

### Bug 22: No Budget = Hard Rejection (Competitors Proceed)

**Symptom**: "7 days in Paris, love art and food, traveling from Mumbai" → rejected for missing budget.

**Impact**: Skyscanner itself doesn't require a budget to search flights. Users exploring ideas shouldn't be forced to commit a number upfront. ChatGPT/Claude/Gemini all proceed with reasonable assumptions.

**Root cause**: The 3-pillar validator at `orchestrator.py:151` requires `budget_total > 0 OR budget_tier`. The tier keyword detector at `routes.py:241` only matches explicit words like "cheap", "backpack", "luxury" — natural phrases like "love art and food" don't trigger any tier.

**Fix direction**:
- Default to "moderate" tier when no budget is mentioned, instead of rejecting
- Or: proceed without a budget and let the LLM estimate based on destination + duration
- Or: return a conversational follow-up asking for budget preference (like competitors do)

---

### Bug 23: Contradictory Budget+Tier Not Flagged

**Symptom**: "$500 budget, luxury 5-star Maldives, 14 days" was accepted and produced a plan. No warning that $500 can't cover even one night at a Maldives resort ($300-800/night average). Budget total returned as null.

**Impact**: User gets a plan that's completely unrealizable. Worse than rejection — it's misleading.

**Root cause**: The budget agent doesn't cross-check `budget_tier` against `budget_total` against `destination_region` costs. The `_llm_analyze()` probably crashed (Bug #2 budget category), fell back to `_fallback_analyze()`, and the null budget_total suggests even the fallback failed.

**Fix direction**:
- After constraint extraction, check if budget_total is realistic for destination × duration × tier
- If the ratio is <30% of minimum viable (e.g., $500 for 14d Maldives luxury), flag with: "Your budget may be insufficient for this trip type. The average cost is approximately $X/day for [tier] travel in [destination]."
- Still generate the plan, but with a prominent warning

---

### Bug 24: 30-Day Trip = 70% Narratives Missing

**Symptom**: 30-day SE Asia trip had 21 out of 30 day narratives empty — only the first 9 days got content.

**Impact**: Scales the narrative truncation bug (#3/#20) to extreme. More than 2/3 of the itinerary has no descriptive content. The trip goes from rich to empty at Day 10.

**Root cause**: Same as Bug #3 — `max_tokens=800` in `orchestrator.py:1299`. For 30 days: 30 × 90 tokens = 2,700 needed. 800 covers ~9 days.

**Fix**: Already documented in Bug #3. Dynamic `max_tokens` would fix all durations.

---

### Bug 25: Vague Destination Intent Not Supported

**Symptom**: "beach trip somewhere tropical 5 days $1500, love snorkeling & sunsets" → rejected as "missing destination"

**Impact**: This is how many casual travelers start — they know what they want to do (beach, snorkeling) but not where. All competitors suggest 2-3 specific destinations to choose from.

**Root cause**: The constraint extraction and 3-pillar validation require a named destination. There's no "destination suggestion" mode.

**Fix direction**:
- When destination is null but preferences are present, use a short LLM call to suggest 2-3 destinations matching the preferences
- Return these as options: "Based on your preferences, we recommend: Bali (Indonesia), Phuket (Thailand), or Zanzibar (Tanzania). Which would you like to explore?"
- This is what ChatGPT does naturally in conversation

---

### Bug 26: ₹50L Budget Returns Stub-Quality Response in 1.1s

**Symptom**: "Ultimate luxury 7-day Switzerland, ₹50,00,000 budget" returned in 1.1 seconds with 7/7 narratives missing, only 1 flight, 5 pins. The comma-separated Indian number format ₹50,00,000 was correctly parsed to 5000000.

**Impact**: The response is clearly a stub/fallback, not a full pipeline output. For a ₹50 lakh trip (the highest budget we've ever seen), the user gets the lowest quality result.

**Root cause**: Likely the LLM pipeline failed silently (Gemini 404 + Groq quota hit) and the stub fallback kicked in. The fast 1.1s time confirms it skipped the LLM agents entirely.

**Fix**: Bugs #8+#9 (Gemini model + key) would restore the primary provider and prevent silent fallback to stubs.

---

### Edge Case Wins (What Worked Well)

1. **Georgia ambiguity** — Correctly resolved "Georgia" as the country (Tbilisi, Sighnaghi, Stepantsminda, Mestia, Batumi), not the US state. The hiking + wine context helped the LLM decide.
2. **1-day minimum** — System handled a 1-day Singapore trip without crashing. Generated 1 day with 6 POI pins.
3. **30-day decomposition** — Multi-country SE Asia (Vietnam, Cambodia, Thailand, Laos) correctly decomposed into 6 cities across 4 countries. The region splitting logic handled 30 days well.
4. **Indian number format** — ₹50,00,000 (Indian lakhs format) correctly parsed to 5,000,000 INR.
5. **Family preferences** — "7-day Bali with 2-year-old toddler" correctly extracted preferences: "kid-friendly activities", "toddler-friendly", "relaxed pace". The LLM understood the implicit needs.
6. **Bali city decomposition** — Correctly generated 4 cities: Denpasar, Ubud, Kuta, Nusa Dua for a 7-day Bali trip.

---

## Round 3: Frontend Template Audit (12 New Bugs)

Deep inspection of `itinerary-display.component.html` revealed **systemic hardcoded content** that makes every non-Iceland trip look broken.

### Bug 27: Currency Symbol Hardcoded as ₹ in Budget Matrix

**Symptom**: Trip Spend Matrix shows `₹` prefix for ALL currencies — a $3000 USD trip shows `₹312,400`, a €5000 EUR trip shows `₹5,000`.

**File**: `src/app/components/itinerary-display/itinerary-display.component.html` lines 459, 467, 475, 483
```html
<div class="text-base font-black text-gray-900 mt-0.5">₹{{ stayCat.amount | number:'1.0-0' }}</div>
```
All four budget categories (stay, transport, food, activities) hardcode `₹`.

**Impact**: Budget breakdown is nonsensical for any non-INR currency. Users see rupee amounts that don't match their budget.

**Fix**: Use `{{ itinerary.constraints.currency }}` or a `getCurrencySymbol()` helper instead of literal `₹`.

---

### Bug 28: Transport Costs Hardcode `$` (Different from Budget Matrix `₹`)

**Symptom**: Transport segments show `$` prefix while the budget matrix shows `₹` — two different hardcoded currency symbols in the same page.

**File**: `itinerary-display.component.html` line 176
```html
${{ segment.estimated_cost_usd | number:'1.0-0' }}
```

**Impact**: Mixed currency symbols on the same page destroys trust. User sees ₹ in the budget but $ in transport.

---

### Bug 29: Flight Prices Use Hardcoded ₹ with ×83 Conversion

**Symptom**: Flight cards always show `₹{{ flight.price * 83 }}` — hardcoding a USD→INR conversion rate of 83.

**File**: `itinerary-display.component.html` line 238
```html
₹{{ (flight.price * (itinerary.constraints.currency === 'INR' ? 1 : 83)) | number:'1.0-0' }}
```

**Impact**: For non-INR users, this multiplies their price by 83 and slaps a ₹ sign on it. A $400 flight shows as ₹33,200 for a European user. The conversion rate 83 is also stale.

---

### Bug 30: Hotel Prices Hardcode `$`

**Symptom**: Hotel cards show `${{ h.price_per_night }}/nt` regardless of user currency.

**File**: `itinerary-display.component.html` line 747
```html
${{ h.price_per_night }}/nt
```

**Impact**: If the API returns prices in INR, the user sees `$12,500/nt` instead of `₹12,500/nt`.

---

### Bug 31: Car Rental Prices Static + Mixed Currency

**Symptom**: Car rental section has three hardcoded fallback options at `$32/day`, `$45/day`, `$68/day` (lines 346, 365, 384) and dynamic prices show `${{ car.price_per_day }}/day (${{ car.total_price }} total / ₹{{ car.total_price * 83 }})` (line 322-323).

**File**: `itinerary-display.component.html` lines 322-323, 346, 365, 384

**Impact**: Static prices are meaningless for non-US destinations. The `* 83` conversion is the same stale hardcoded rate.

---

### Bug 32: "Money-Saving Tips" Are Hardcoded Iceland Content

**Symptom**: Every destination shows three Iceland-specific money tips:
1. "N1 Prepaid Fuel Card" — references KEF airport and ₹3,500 savings
2. "Self-Catering via Bónus Supermarkets" — references Skyr, smoked lamb, pink pig stores
3. "Free Natural Hot Springs" — references Blue Lagoon ($120/p) and Reykjadalur

**File**: `itinerary-display.component.html` lines 420-442

**Impact**: A user planning a trip to Bali, Japan, or NYC sees tips about Iceland gas stations and Blue Lagoon. Extremely confusing and destroys credibility.

**Root cause**: The `@else` fallback (line 419) renders hardcoded Iceland tips when the API doesn't return dynamic tips. Since `insights.money_saving_tips` is often empty, the fallback shows for most trips.

---

### Bug 33: "Smart Swap" Hardcoded as Iceland Hotel

**Symptom**: The suggested swap card always shows: "Hotel Kría → Guesthouse Carina in Vík saves ₹5,500/night" — an Iceland-specific hotel swap.

**File**: `itinerary-display.component.html` line 493
```html
<span class="font-bold">Smart Swap:</span> Hotel Kría → Guesthouse Carina in Vík saves ₹5,500/night.
```

**Impact**: Shown on every trip. A Japan traveler sees a suggestion to switch to a guesthouse in Vík, Iceland.

---

### Bug 34: Driving Route Card Shown Unconditionally (Iceland Content)

**Symptom**: Every day shows an amber "Driving Route" card with:
- "Route 1 Paved" badge (line 593) — Iceland's Ring Road
- "N1 Gas Station (Every 60-80 km)" (line 600)
- "Bridge Alert: Single-lane bridges along glacial sands" (line 604)
- "Verified sunlight hours: 07:30 - 18:45" (line 613) — Iceland winter hours
- Fallback driving time "2.5 hrs to next stop" (line 571) and "Route 1 Ring Highway" (line 573)

**File**: `itinerary-display.component.html` lines 585-614

**Impact**: A city trip to Tokyo shows warnings about single-lane bridges on glacial sands. There's no `@if` guard — it renders for ALL destinations, not just road trips.

**Fix**: Wrap in `@if (itinerary.constraints.is_road_trip)` and use dynamic content from the API.

---

### Bug 35: Fallback Hotel is Always "Hotel Kría" (Iceland)

**Symptom**: When a day has no hotel data from the API, the fallback displays "Hotel Kría ({{ city }})" at $220/nt.

**File**: `itinerary-display.component.html` line 808
```html
<h5 class="text-xs sm:text-sm font-bold text-gray-900">Hotel Kría ({{ activeDay.city.split('&')[0].trim() }})</h5>
```

**Impact**: "Hotel Kría (Tokyo)" or "Hotel Kría (Goa)" makes no sense. Hotel Kría is a real hotel in Vík, Iceland.

---

### Bug 36: "Compare Other Blueprints" Are Static

**Symptom**: Three comparison blueprints are hardcoded regardless of current trip:
- Option B: "Tokyo & Kyoto (10 Days)" — Est. ₹2,90,000
- Option C: "Sikkim Monasteries (8 Days)" — Est. ₹1,15,000
- Option D: "Swiss Alps Trains (9 Days)" — Est. ₹3,40,000

**File**: `itinerary-display.component.html` lines 838-872

**Impact**: If the user already planned a Japan trip, Option B suggests... another Japan trip. Alternatives should be contextual (similar budget, different destinations).

---

### Bug 37: Longitude Always Shows "°W" (Wrong for Eastern Hemisphere)

**Symptom**: Map pins display `{{ pin.lng.toFixed(3) }}°W` — always "West" even for Eastern Hemisphere destinations.

**File**: `itinerary-display.component.html` line 1017
```html
{{ pin.lat.toFixed(3) }}°N, {{ pin.lng.toFixed(3) }}°W
```

**Impact**: Tokyo (139.6°E) shows as 139.6°W (Pacific Ocean). Bali, India, Europe — all Eastern Hemisphere destinations show wrong cardinal direction. Should use conditional N/S and E/W based on sign.

---

### Bug 38: "Full 11-Day Journey Overview" Hardcodes Duration

**Symptom**: The remaining days summary table header says "Full 11-Day Journey Overview" regardless of actual trip duration.

**File**: `itinerary-display.component.html` line 880
```html
<h4 class="text-sm font-extrabold text-gray-900">Full 11-Day Journey Overview</h4>
```

**Impact**: A 5-day Goa trip shows "Full 11-Day Journey Overview". Should use `{{ itinerary.days.length }}-Day`.

---

### Bug 39: Frontend Always Sends currency: "USD" to Backend

**Symptom**: The Angular component hardcodes 'USD' in the API call regardless of the user's prompt currency.

**File**: `src/app/components/ai-travel-planner/ai-travel-planner.component.ts` line 147
```typescript
this.plannerService.generatePlan(text, useStub, origin, date, 'USD')
```

And the service defaults to USD at line 40:
```typescript
...(currency ? { currency: currency.trim() } : { currency: 'USD' })
```

**Impact**: Even when the user types "₹3.5L budget", the API payload sends `"currency": "USD"`. The backend's LLM extraction may override this from the prompt text, but it creates a conflict — the explicit payload currency vs. the inferred prompt currency.

---

### Bug 40: Error Messages Show Raw JSON to Users

**Symptom**: When the backend returns a 4xx error (like missing constraints), the frontend dumps raw JSON as the error message.

**File**: `src/app/services/travel-planner.service.ts` line 85
```typescript
this.errorMessage.set(typeof error.error.detail === 'string' 
  ? error.error.detail 
  : JSON.stringify(error.error.detail));
```

**Impact**: User sees `{"error":"missing_constraints","message":"Please provide...","missing_fields":["budget"],"suggested_tiers":[...]}` instead of a friendly message. The backend actually sends a well-structured error with `message` and `suggested_tiers` fields — the frontend should parse and display them.

---

### Bug 41: Review Agent Hardcodes `$` in Budget Check Message

**Symptom**: The review agent's budget validation message always uses `$` regardless of trip currency.

**File**: `backend/app/agents/review.py` line 144
```python
message=f"Budget: ${total} vs limit ${budget}"
```

**Impact**: A ₹10L trip shows "Budget: $195912 vs limit $1000000" in the review output. Minor since this is internal, but leaks to any debug/review display.

---

### Bug 42: No Group Size / Traveler Count Support

**Symptom**: "5-day Goa trip for 6 friends, 30000 INR per person budget" → system extracts budget as 30000 for 1 person, not 180000 for 6.

**File**: `backend/app/models/schemas.py` lines 78-127 — `TravelConstraints` has no `group_size` or `travelers` field. `backend/app/llm/groq_client.py` lines 147-212 — extraction prompt doesn't ask for group size.

**Impact**: Group travel budgets are wrong by Nx (where N = group size). Flight search uses 1 adult. Hotel recommendations don't account for room needs. This affects every group trip, family trip, or couples trip.

---

### Bug 43: No Accessibility Support

**Symptom**: "10-day accessible trip to Japan for wheelchair user" → accessibility need only captured in `preferences` array, no structural adaptation.

**File**: Same as Bug 42 — `TravelConstraints` has no `accessibility_needs` field.

**Impact**: Wheelchair users get the same temple staircase routes as able-bodied travelers. No accessible hotel filtering, no accessible transport recommendations, no activity filtering for mobility limitations. Competitors at least acknowledge accessibility in their responses.

---

## Round 3: API Test Results (Round 2 Edge Cases)

### Tests Completed

| # | Prompt | Status | Time | Key Issues |
|---|--------|--------|------|------------|
| 1 | Group of 6 friends, Goa, ₹30k/person | OK | 128.6s | Budget=30000 USD (not ₹, not ×6), Iceland pin 1/6, Duffel/AUD |
| 2 | Family with toddler, Bali, $4000 | OK | 56.1s | Good extraction (kid-friendly prefs), Iceland pins 4/21, Duffel/AUD |
| 3 | Wheelchair accessible, Japan, $5000 | ERROR | 79.4s | brotli decoder crash — response too large for decompression |
| 4 | NYC Dec 25-30, $3000 | OK | 52.5s | Date correctly extracted (2026-12-25), Iceland pin 1/6, Duffel/AUD |
| 5 | Rajasthan heritage train, ₹80k | OK | 120.7s | 4 cities correct, 0 flights (good!), 7 transport segments, currency=USD not INR, 8/8 narratives missing, Iceland 4/21 |
| 6 | Honeymoon Santorini+Mykonos, €5k | STUB | 0.1s | Pipeline failed → stub. Mykonos dropped, "romantic/honeymoon" lost, 10/10 narratives missing, origin lost |
| 7 | Round trip Munich→Austria→Croatia | STUB | 0.2s | Pipeline failed → stub. Only "Munich" captured, 4 countries dropped, not recognized as road trip, 14/14 narratives missing |
| 8 | Weekend getaway Pondicherry, ₹5k | 400 | 0.1s | "Weekend" not mapped to 2 days → rejected as "missing duration" |
| 9 | Ultra-long Portugal prompt (7 days, Lisbon+Porto+Sintra) | STUB | 0.1s | Pipeline failed → stub. 7 days→3, 3 cities→"Portugal", all preferences lost, origin lost |
| 10 | Hindi+English "Mujhe 7 din ka Kerala trip" | 500 | 0.1s | Internal server error: `int()` on empty string — LLM can't parse Hindi |

### Round 2 Findings Summary

**Group travel (Test 1)**: System has zero concept of group size. "30000 INR per person for 6 friends" → extracted as 30000 USD total for 1 person. Three bugs compounded: no group size field, currency forced to USD by frontend, and "per person" budget not multiplied.

**Family travel (Test 2)**: Positive — LLM correctly inferred "toddler-friendly", "relaxed pace", "family-friendly" as preferences. But structurally identical to any other trip: no nap time scheduling, no stroller accessibility notes, no child-safe activity filtering.

**Accessibility (Test 3)**: HTTP client error (brotli decompression failure) — couldn't even test if accessibility was captured.

**Dates (Test 4)**: Win — `start_date: "2026-12-25"` correctly extracted from "December 25-30 2026". Seasonal activity awareness not tested.

**Domestic train (Test 5)**: Mixed — correctly generated 4 cities and 0 flights (appropriate for domestic rail), but ₹80,000 captured as 80000 USD, and all 8 narratives missing (even a sub-12-day trip can lose all narratives in the stub fallback path).

**Honeymoon (Test 6)**: Complete failure — 0.1s stub response. Mykonos dropped, romantic/honeymoon context lost, generic "Scenic landscapes" preferences substituted. The Groq token limit caused silent pipeline failure.

**Round trip (Test 7)**: Complete failure — stub response. "Starting and ending in Munich: Austria, Slovenia, Croatia, Montenegro" → only "Munich" captured as single city. 4 countries completely lost. Not recognized as road trip.

**Weekend (Test 8)**: "Weekend getaway" not parsed as 2 days → rejected for "missing duration". Bug #44.

**Verbose prompt (Test 9)**: Catastrophic loss — the most detailed prompt in the test suite (mentions Lisbon 3d, Porto 2d, Sintra day trip, vegetarian, boutique hotels, specific bookshop) → stub with "3 days in Portugal". All rich detail discarded. This is the worst failure mode: a highly specific, well-structured prompt gets LESS useful results than a simple one.

**Hindi+English (Test 10)**: HTTP 500 crash — `invalid literal for int() with base 10: ''`. The LLM couldn't parse mixed-language input and returned empty values that caused a Python crash. Bug #45.

### New Bugs from Round 2

### Bug 44: "Weekend" Not Parsed as Duration

**Symptom**: "Weekend getaway to Pondicherry" → rejected as "missing duration"

**Root cause**: Neither the regex duration extractor in `routes.py` nor the LLM constraint extraction prompt includes "weekend" → 2 days mapping.

**File**: `backend/app/api/routes.py` (regex) and `backend/app/llm/groq_client.py` line 182 (LLM prompt says "Extract duration in days (e.g. 1 week = 7 days)" but doesn't mention weekend).

**Impact**: "Weekend getaway" is one of the most common travel phrases. All competitors handle it.

---

### Bug 45: Hindi+English Input Causes HTTP 500

**Symptom**: "Mujhe 7 din ka Kerala trip plan karo, budget 50000 rupees" → HTTP 500 with `invalid literal for int() with base 10: ''`

**Root cause**: The LLM returned malformed JSON when processing mixed Hindi+English. A numeric field (likely `duration_days`) was extracted as an empty string, which Python's `int()` couldn't parse. No input validation catches this before the crash.

**Impact**: Any non-English input crashes the server. For an Indian-market product (₹ budgets, Indian city suggestions), this is critical — many Indian users code-switch between Hindi and English naturally.

---

### Bug 46: Groq Token Exhaustion → Silent Stub Degradation

**Symptom**: Tests 6, 7, 9 all returned in 0.1-0.2s with generic stub responses when Groq daily tokens hit ~80%.

**Root cause**: When the Groq LLM call fails due to quota exhaustion, the system silently falls back to `_generate_enriched_stub_response()` in `routes.py`. This stub:
- Uses only regex to extract constraints (lossy)
- Returns generic "Discovery Journey" titles
- Has 0 narratives, 0 transport segments, minimal pins
- Shows no indicator to the user that they got a degraded response

**Impact**: Users unknowingly receive a severely degraded product. The backend health endpoint shows token usage, but the frontend has no awareness. A user who plans a trip at 11 PM (when daily tokens are exhausted) gets a response 10× worse than one who plans at 8 AM.

**File**: `backend/app/api/routes.py` lines 155-269 (stub fallback), `backend/app/llm/groq_client.py` lines 338-385 (retry with fallback model)

**Fix direction**: 
- Show a banner: "Running in fast mode — some details may be missing. Full AI pipeline resets at midnight UTC."
- Or queue the request and process it when tokens refresh
- Or use Gemini as a real fallback (requires fixing bugs #8+#9 first)

---

## Final Priority Matrix (All 46 Issues)

| Priority | Bug | Impact | Effort |
|----------|-----|--------|--------|
| **P0** | #8 Gemini model deprecated | Failover chain broken | 5 min |
| **P0** | #9 Gemini API key expired | Same | 5 min |
| **P0** | #10 Duplicate city crash | Ring routes fail completely | 10 min |
| **P0** | #15 "Duffel Airways" shown | Trust-destroying fake airline | 15 min |
| **P0** | #2 Budget category crash | Budget shows nonsense | 30 min |
| **P0** | #4 Map pins = Iceland | Map is completely wrong | 1 hour |
| **P0** | #16 ₹ on USD amounts | Budget numbers nonsensical | 30 min |
| **P0** | #27 Budget matrix hardcodes ₹ | Wrong symbol for all non-INR | 15 min |
| **P0** | #32 Iceland money tips on ALL trips | Blue Lagoon tips for Japan users | 15 min |
| **P0** | #34 Iceland driving card unconditional | Glacial bridge alerts in Tokyo | 15 min |
| **P1** | #21 Multi-city cross-country rejected | Common trip pattern blocked | 1 hour |
| **P1** | #22 No budget = hard rejection | Too strict vs competitors | 30 min |
| **P1** | #13 Flights always AUD | Prices meaningless | 1 hour |
| **P1** | #12 Budget math wrong everywhere | Core value prop broken | 2 hours |
| **P1** | #11 Hotels ignore budget tier | Luxury user gets Premier Inn | 1 hour |
| **P1** | #1 Route design (scenic drives) | Plan quality vs competitors | 2 hours |
| **P1** | #3/#20/#24 Narrative truncation | Days 8+ look empty | 15 min |
| **P1** | #6 No practical info | Major gap vs all competitors | 2 hours |
| **P1** | #17 City breadcrumb duplication | Looks broken to users | 30 min |
| **P1** | #18 Iceland alerts on Sweden | Content accuracy | 30 min |
| **P1** | #25 Vague destination not supported | Casual users blocked | 2 hours |
| **P1** | #28 Transport costs hardcode `$` | Mixed symbols on same page | 10 min |
| **P1** | #29 Flight price ×83 INR conversion | Wrong for all non-USD users | 20 min |
| **P1** | #30 Hotel prices hardcode `$` | Wrong currency on hotel cards | 10 min |
| **P1** | #33 Smart Swap hardcoded Iceland hotel | "Switch to Guesthouse in Vík" for all trips | 15 min |
| **P1** | #35 Fallback hotel = Hotel Kría | "Hotel Kría (Tokyo)" shown | 10 min |
| **P1** | #39 Frontend sends currency: USD always | Backend may use wrong currency | 15 min |
| **P1** | #42 No group size support | Group budgets wrong by Nx | 2 hours |
| **P1** | #44 "Weekend" not parsed as duration | Common phrase rejected | 15 min |
| **P1** | #45 Hindi+English crashes server (500) | Indian users locked out | 1 hour |
| **P1** | #46 Silent stub degradation on quota | Unknowingly 10× worse product | 2 hours |
| **P2** | #23 Contradictory budget not flagged | Misleading plans generated | 1 hour |
| **P2** | #14 Groq quota hit fast | Fixed by #8+#9 | 0 min |
| **P2** | #7 "$3,000" budget format | Some prompts rejected | 30 min |
| **P2** | #19 "Open 24 hrs" on museums | Minor trust issue | 15 min |
| **P2** | #26 Stub response for expensive trips | Silent quality degradation | Fixed by #8+#9 |
| **P2** | #31 Car rental static prices + ×83 | Irrelevant car prices shown | 20 min |
| **P2** | #36 Compare Blueprints are static | Suggests Japan for Japan trip | 1 hour |
| **P2** | #37 Longitude always "°W" | Eastern Hemisphere is "West" | 5 min |
| **P2** | #38 "11-Day" hardcoded in header | Wrong for all other durations | 5 min |
| **P2** | #40 Error messages show raw JSON | Bad UX on 400 errors | 30 min |
| **P2** | #41 Review agent hardcodes `$` | Budget check shows wrong symbol | 5 min |
| **P2** | #43 No accessibility support | Wheelchair users get stairs | 3 hours |
| **P3** | Summary tab broken | Missing feature | 1 hour |
| **P3** | Top-level hotel_options empty | Data gap | 30 min |
| **P3** | Map is SVG not Google Maps | No terrain/satellite tiles | 4 hours |

### Critical Path Analysis

**P0 (10 bugs, ~3 hours)**:
- Backend config: #8+#9 (10 min) → #10+#15 (25 min) → #2 (30 min) → #4 (1 hour)
- Frontend template purge: #16+#27+#32+#34 (45 min) — remove all hardcoded ₹, Iceland content, and unconditional road trip cards

**P1 (21 bugs, ~17 hours)**:
- Currency systemwide: #28+#29+#30+#33+#35+#39 (~1.5 hours) — create a `getCurrencySymbol()` helper, replace all hardcoded `$` and `₹`, remove ×83 conversion, make frontend send detected currency
- Input handling: #21+#22+#25+#44+#45 (4 hours) — multi-city, no-budget, vague destination, "weekend" parsing, Hindi crash
- Quality: #1+#3+#6+#12+#42 (~8 hours) — route design, narratives, practical info, budget math, group travel
- Resilience: #46 (2 hours) — show degradation banner when Groq quota exhausted, don't silently serve stubs

**P2 (12 bugs, ~6.5 hours)**: Polish and edge cases.

**Total P0+P1+P2: ~26.5 hours of work.**

### The "Iceland Template" Meta-Bug

Bugs #16, #18, #32, #33, #34, #35 are all symptoms of ONE root cause: **the frontend was built and tested exclusively with an Iceland road trip demo, and hardcoded Iceland-specific content was used as placeholder that was never made dynamic.** This affects:
- Money-saving tips (Iceland gas stations, Bónus supermarkets, Blue Lagoon)
- Smart swap suggestion (Hotel Kría → Guesthouse Carina in Vík)
- Driving route card (Route 1, N1 stations, glacial bridge alerts)
- Fallback hotel (Hotel Kría)
- Sunlight hours (07:30-18:45)
- Currency (₹ hardcoded for the India-to-Iceland demo)

**A single "template purge" sprint would fix 6 bugs at once.** Replace all hardcoded content with API-driven dynamic content, and add `@if` guards for road-trip-only sections.

### The "Currency Chaos" Meta-Bug

Bugs #5, #13, #16, #27, #28, #29, #30, #31, #39, #41 are all symptoms of **no unified currency handling**. The system has at least 4 conflicting currency behaviors:
1. Frontend sends `"USD"` always (#39)
2. Budget matrix hardcodes `₹` (#27)
3. Transport/hotels hardcode `$` (#28, #30)
4. Flights hardcode `₹` with ×83 conversion (#29)
5. Duffel API returns AUD (#13)
6. Backend review agent hardcodes `$` (#41)

**Fix**: Create a `CurrencyPipe` in Angular that reads `itinerary.constraints.currency` and formats with the correct symbol. Apply it everywhere. On the backend, pass currency to Duffel API and normalize all prices.

**Strategic note**: Fixing just the 10 P0 bugs (3 hours) transforms the product from "broken prototype with Iceland content everywhere" to "working demo." The 17 P1 bugs make it competitive. The meta-bug analysis shows that 60% of the frontend bugs trace to two root causes (Iceland template + currency chaos) that can be fixed in focused sprints.

---

## Test Reproducibility

All tests are saved as JSON:
- `backend/sweden_test_output.json`
- `backend/japan_test_output.json`
- `backend/test_india_domestic.json`
- `backend/test_europe_multicity.json`
- `backend/test_backpacker.json`
- `backend/test_luxury_short.json`

Run via:
```python
from app.agents.orchestrator import OrchestratorAgent
agent = OrchestratorAgent()
result = await agent.create_plan('Plan a 12-day Sweden, ₹10L budget, love nature and scenic drives')
```
