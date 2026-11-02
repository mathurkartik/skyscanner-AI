# AI Travel Planner — Improvement Spec v3 (Dynamic + Multi-Modal)

> **Principles**:
> 1. Everything dynamic — no hardcoded curated data, no static IATA dictionaries.
> 2. Multi-modal transport — the LLM decides if a segment needs a flight, train, bus, or car.
> 3. Dual-provider LLM — Gemini primary + Groq fallback for reliability and throughput.
> 4. Any destination worldwide — 7,000+ airports, any city pair, any transport mode.
>
> **Tested with**: France 10-day, Norway 11-day — both confirmed all issues below.
> **Date**: 2026-11-02

---

## 1. LLM Provider Strategy: Gemini + Groq Dual-Provider

### Why Switch to Gemini as Primary?

| Metric | Gemini 2.5 Flash (Free) | Groq gpt-oss-120b (Free) |
|--------|------------------------|--------------------------|
| **TPM** | ~250,000 | **8,000** (30x less) |
| **Daily token cap** | No hard cap documented | **200,000 TPD** |
| **JSON mode** | Yes (`response_mime_type`) | No (dropped for gpt-oss) |
| **RPM** | ~10-15 | ~30 |

Gemini's 250k TPM means the multi-agent pipeline can run **all LLM calls in parallel** instead of serializing them behind Groq's 8k TPM bottleneck. This alone could cut plan generation time from 60s to 15-20s.

### Implementation: Dual-Provider with Auto-Failover

**Current** (`backend/app/llm/__init__.py`):
```python
def get_llm_client():
    if settings.llm_provider == "gemini": return get_gemini_client()
    if settings.llm_provider == "groq": return get_groq_client()
```

**Target**: New `ResilientLLMClient` wrapper:
```python
class ResilientLLMClient:
    """Tries primary provider, falls back to secondary on rate limit/quota."""
    
    def __init__(self):
        self.primary = get_gemini_client()    # High throughput
        self.secondary = get_groq_client()    # Fallback
    
    async def chat_with_retry(self, **kwargs):
        try:
            return await self.primary.chat_with_retry(**kwargs)
        except (RateLimitError, QuotaExceeded):
            return await self.secondary.chat_with_retry(**kwargs)
```

**Multiple keys**: Two Gemini keys from **two different Google accounts** = double quota (same account shares quota). Set `GEMINI_API_KEY` and `GEMINI_API_KEY_2` in `.env`.

**Config changes** (`backend/app/config.py`):
```python
gemini_api_key_2: str | None = None    # Second Google account key
llm_failover: bool = True              # Enable auto-failover
```

---

## 2. Multi-Modal Transport Architecture

### The Problem
Currently the pipeline **always searches for flights** regardless of whether the trip needs them:
- Gandhinagar → Sholapur (800km domestic India) = should suggest **train** (Rajdhani/Shatabdi)
- Zurich → Lucerne → Interlaken (Switzerland) = should suggest **SBB train**
- Paris → Lyon (470km) = **TGV train** (2 hours) makes more sense than a flight
- Mumbai → Paris = **flight** (obviously)
- Iceland Ring Road = **car rental** (already works)

### The Solution: Let the LLM Decide Transport Mode

**Step 1**: Enhance constraint extraction prompt to include `transport_segments`:

```json
{
  "destination_region": "India",
  "cities": ["Gandhinagar", "Sholapur"],
  "origin_city": "Gandhinagar",
  "transport_segments": [
    {
      "from": "Gandhinagar",
      "to": "Sholapur",
      "recommended_mode": "train",
      "reason": "800km domestic route, well-connected by Indian Railways",
      "estimated_duration_hours": 12,
      "estimated_cost_usd": 25
    }
  ]
}
```

The LLM already knows:
- Indian Railways connects Gandhinagar and Sholapur (no direct flight exists)
- TGV Paris→Lyon takes 2 hours and costs €19-80
- Shinkansen Tokyo→Kyoto takes 2h15m and costs ¥13,320
- SBB Zurich→Lucerne takes 45 minutes
- No train exists Mumbai→Paris, so it must be a flight

**Step 2**: The Logistics Agent already supports this! `_llm_generate_movements()` returns `mode: "train|bus|flight|drive|ferry"`. But `search_flights()` is called separately and **ignores** the movement plan. Fix: only call the flight client when a movement segment has `mode: "flight"`.

**Step 3**: For each transport mode, generate appropriate booking info:

| Mode | What to Show | Booking Link |
|------|-------------|-------------|
| **flight** | Airline, route, price, stops | Kiwi Tequila deeplink or Skyscanner |
| **train** | Train name, class, duration, price | trainline.com / irctc.co.in / sbb.ch |
| **bus** | Operator, duration, price | redbus.in / flixbus.com |
| **drive** | Distance, fuel cost, route highlights | Google Maps directions link |
| **ferry** | Operator, port, duration, price | directferries.com |

**Step 4**: Drop the static IATA dictionary. The `CITY_TO_IATA` dict in `flight_client.py` has ~150 cities. There are 7,000+ airports. Instead:
- For flight segments: ask the LLM to return the IATA codes (it knows BOM, DEL, CDG, OSL, etc.)
- Or use a lightweight airport lookup API (free: aviationstack.com 100 req/mo, or just let the LLM handle it)
- The LLM is more accurate than a static dict — it knows that "Gandhinagar" → nearest airport is AMD (Ahmedabad), not that there's no airport

### Frontend Changes for Multi-Modal

Current UI shows:
- "Live Flight Matches" section (always visible)
- "Ring Road Vehicle Rental" section (hardcoded)

**Target UI**:
- "Getting There" section showing the recommended transport for arrival (flight, train, etc.)
- "Between Cities" section showing inter-city transport (can be different modes per segment)
- Vehicle rental section only when `is_road_trip: true` or LLM recommends driving

---

## 3. Data Layer: Dynamic API Stack

### Flights (only when LLM recommends flight mode)

| Priority | Source | Free Tier |
|----------|--------|-----------|
| **Primary** | Kiwi Tequila API | Free for testing |
| **Fallback** | LLM-estimated (Gemini/Groq) | Realistic airline + price + duration |

Delete `_generate_realistic_fallback()` and its 4 hardcoded route cases. Delete `CITY_TO_IATA` dictionary.

### Hotels

| Priority | Source | Free Tier |
|----------|--------|-----------|
| **Primary** | Booking.com Affiliate | Free (affiliate signup) |
| **Fallback** | LLM-estimated | Real hotel names + prices per city |

Delete `CURATED_HOTELS` and `KNOWN_DESTINATIONS` dictionaries.

### POIs / Attractions

| Priority | Source | Free Tier |
|----------|--------|-----------|
| **Primary** | Google Places (existing key) | ~5,000-10,000 calls/mo |
| **Secondary** | OpenTripMap | 5,000 req/day, free |
| **Fallback** | LLM-generated | Attraction details for any city |

Delete `CURATED_PLACES` dictionary.

### Geocoding / Map Pins

| Priority | Source | Free Tier |
|----------|--------|-----------|
| **Primary** | Google Geocoding (existing key) | 10,000/mo |
| **Fallback** | LLM-estimated coordinates | Approximate lat/lng |

Delete hardcoded Iceland/Japan map pin generation in orchestrator.

---

## 4. Pipeline Bugs (Non-API)

### UTF-8 Encoding Corruption
**Symptom**: "MusÃ©e" instead of "Musée".
**Fix**: Ensure UTF-8 throughout — check `groq_client.py` response decoding, FastAPI `json.dumps(ensure_ascii=False)`.

### Flat $100/Day Activity Costs
**Fix**: Add `estimated_cost_usd` to the LLM activity generation prompt. The LLM knows real prices.

### Budget Rollup Empty
**Fix**: Once transport and hotels return dynamic data, budget agent can sum them. Defensive: LLM-estimate missing categories.

### Hardcoded "Ring Road Vehicle Rental" / "KEF Airport Pickup"
**Fix**: Dynamic heading from itinerary data. Show only when `car_estimates.length > 0`.

### Generic Cost-Saving Tips
**Fix**: LLM-generate destination-specific tips in the Review Agent.

### Route Map Shows Iceland for Non-Iceland
**Fix**: Generate dynamic map from map_pins, or hide when not a road trip.

---

## 5. New Features Status

| Feature | Frontend | Backend | Status |
|---------|----------|---------|--------|
| Origin city input | ✅ Done | ❌ Need `origin_city` in constraints + API | Frontend merged |
| Travel date picker | ✅ Done | ❌ Need `start_date` in constraints + API | Frontend merged |
| Currency consistency | ✅ USD default | ❌ Backend defaults to INR | Config change |
| Multi-modal transport | ❌ UI needs redesign | ❌ Need transport_segments in constraints | New |
| Dual-provider LLM | N/A | ❌ Need ResilientLLMClient wrapper | New |

---

## 6. Implementation Phases

| Phase | What | Effort | Impact |
|-------|------|--------|--------|
| **1** | Switch `LLM_PROVIDER=gemini`, test pipeline | 30 min | 30x more throughput |
| **2** | Add `ResilientLLMClient` (Gemini→Groq failover) | 1 hour | Never hits quota wall |
| **3** | Wire `origin_city` + `start_date` from frontend → backend | 2 hours | Flights use real origin & date |
| **4** | Add `transport_segments` to constraint extraction | 2 hours | LLM decides flight vs train vs bus |
| **5** | Replace flight/hotel/POI fallbacks with LLM-estimated | 3 hours | Works for ANY destination |
| **6** | Delete all static dictionaries (CURATED_*, CITY_TO_IATA) | 1 hour | ~855 lines removed |
| **7** | Fix UTF-8, flat costs, budget rollup, generic tips | 2 hours | Output quality |
| **8** | Dynamic map pins via geocoding | 1 hour | Map shows real locations |
| **9** | Frontend: multi-modal transport UI | 3 hours | Shows train/bus/car, not just flights |
| **10** | Integrate Kiwi Tequila + Booking.com Affiliate | 3 hours | Real live data |

**Total**: ~19 hours. Phases 1-3 are quick wins. Phase 4 is the architecture shift.

---

## 7. What to Delete (Total: ~855 lines of static data)

| File | What | Lines |
|------|------|-------|
| `flight_client.py` | `CITY_TO_IATA` dict (150 cities) | ~150 lines |
| `flight_client.py` | 4 hardcoded route cases in `_generate_realistic_fallback()` | ~200 lines |
| `hotel_client.py` | `CURATED_HOTELS` dict | ~180 lines |
| `hotel_client.py` | `KNOWN_DESTINATIONS` dict | ~35 lines |
| `google_places_client.py` | `CURATED_PLACES` dict | ~400 lines |
| `orchestrator.py` | Hardcoded Iceland/Japan map pins | ~20 lines |
| `orchestrator.py` | Static `cost_saving_tips_v2` | ~20 lines |

Replaced by: ~80 lines of LLM prompt templates that work for any destination worldwide.

---

## 8. What Works Well (Keep)

- LLM-generated **activities** — rich, accurate, well-paced for any destination
- **Strategic insight** and **why_this_plan** — thoughtful, destination-specific
- **Multi-region splitting** — correct day allocation across cities
- **5-agent pipeline** — sound architecture, just needs dynamic data
- **Budget analysis prose** — smart budget tier detection
- **Movement planning** (`_llm_generate_movements`) — already supports train/bus/drive/ferry
- **Origin city + date picker UI** — already implemented and tested
- **Gemini client** — fully integrated, drop-in replacement, supports JSON mode

---

## 9. API Keys Summary

| API | Env Var | Status | Action |
|-----|---------|--------|--------|
| Groq | `GROQ_API_KEY` | ✅ Active | Keep as fallback |
| Gemini | `GEMINI_API_KEY` | ❌ Needed | Get from ai.google.dev |
| Gemini #2 | `GEMINI_API_KEY_2` | ❌ Optional | Second Google account for double quota |
| Google Places | `GOOGLE_PLACES_API_KEY` | ⚠️ Verify | Test with curl |
| Kiwi Tequila | `KIWI_API_KEY` | ❌ Phase 10 | tequila.kiwi.com |
| Booking.com | `BOOKING_AFFILIATE_ID` | ❌ Phase 10 | booking.com/affiliate |
| OpenTripMap | `OPENTRIPMAP_API_KEY` | ❌ Optional | opentripmap.io |
