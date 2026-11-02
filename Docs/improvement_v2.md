# AI Travel Planner — Improvement Spec v2 (Dynamic-First)

> **Principle**: Everything must be dynamic and API-driven. No hardcoded curated data.
> A Skyscanner clone should pull real data for any destination, not maintain static inventories.
> **Tested with**: France 10-day, Norway 11-day — both confirmed all issues below.
> **Date**: 2026-11-02

---

## Architecture: Current vs. Target

### Current (Broken)
```
User Prompt → LLM extracts constraints → Agents query tools
                                              ↓
                                    Tools check: RapidAPI enabled?
                                    ├── Yes → Call API (disabled, quota exhausted)
                                    └── No → Return CURATED_HOTELS / CURATED_PLACES
                                              (only Iceland/Japan have entries)
                                              → Everything else = empty []
```

### Target (Dynamic)
```
User Prompt + Origin + Date → LLM extracts constraints → Agents query tools
                                                              ↓
                                                    Tools try API cascade:
                                                    1. Primary free API (Kiwi/Google/Booking)
                                                    2. LLM-estimated data (Groq generates realistic results)
                                                    3. Never returns empty []
```

**Key shift**: Replace static `CURATED_*` dictionaries with **LLM-generated estimates** as the universal fallback. The LLM already knows hotel price ranges, airline routes, and attraction details for every city in the world — use that knowledge instead of maintaining hardcoded data.

---

## Data Layer: Free API Stack

### Flights

| Priority | Source | Free Tier | What it Returns |
|----------|--------|-----------|-----------------|
| **Primary** | **Kiwi Tequila API** | Free for low-volume/testing | Real flight offers, prices, airlines, booking links |
| **Fallback** | **LLM-estimated routes** | Uses existing Groq quota | Realistic airline + price + stops based on origin→destination |

**Implementation** (`backend/app/tools/flight_client.py`):
1. Register at [Kiwi Tequila](https://tequila.kiwi.com/) — free API key for testing.
2. Add `KIWI_API_KEY` to config.py and .env.
3. New method `_query_kiwi_api()` — call `https://api.tequila.kiwi.com/v2/search` with origin IATA, destination IATA, date, passengers.
4. Replace `_generate_realistic_fallback()` hardcoded 4-route engine with an LLM call:
   ```
   Prompt: "Generate 3 realistic flight options from {origin} to {destination} 
   departing {date}. Return JSON with: airline, flight_number, price_usd, 
   duration_hours, stops, layover_city. Use real airline names and realistic 
   2026 pricing."
   ```
5. **Delete** the hardcoded India→Iceland/Australia/Japan route cases.
6. **Delete** the `"DEL"` default in `resolve_iata()` — use `origin_city` from constraints.

**Why not Amadeus?** Amadeus Self-Service API shuts down July 17, 2026 — dead end.
**Why not RapidAPI flights-sky?** 500 req/month free tier already exhausted.

---

### Hotels

| Priority | Source | Free Tier | What it Returns |
|----------|--------|-----------|-----------------|
| **Primary** | **Booking.com Affiliate API** | Free (affiliate program) | Real availability, prices, deep links |
| **Fallback** | **LLM-estimated hotels** | Uses existing Groq quota | Realistic hotel names, prices, neighborhoods per city |

**Implementation** (`backend/app/tools/hotel_client.py`):
1. Apply for [Booking.com Affiliate Partner](https://www.booking.com/affiliate-program.html) — free, returns real data.
2. Replace `_generate_fallback_hotels()` with an LLM call:
   ```
   Prompt: "Generate 3 real hotels in {city} for a {budget_tier} traveler.
   Return JSON: name (real hotel), price_per_night_usd, star_rating, 
   neighborhood, one-line description. Use actual hotel names that exist."
   ```
3. **Delete** entire `CURATED_HOTELS` dictionary (~200 lines of static data).
4. **Delete** `KNOWN_DESTINATIONS` static lookup — use geocoding API instead (see below).
5. Keep the RapidAPI booking-com15 path as a third option (if user re-enables).

---

### POIs / Attractions

| Priority | Source | Free Tier | What it Returns |
|----------|--------|-----------|-----------------|
| **Primary** | **Google Places API** (existing key) | ~5,000-10,000 calls/mo | Name, rating, reviews, photos, hours, coords |
| **Secondary** | **OpenTripMap** | 5,000 req/day | Attractions from Wikipedia/Wikidata with coords |
| **Fallback** | **LLM-generated** | Uses existing Groq quota | Attraction details for any city |

**Implementation** (`backend/app/tools/google_places_client.py`):
1. **Verify** the existing `GOOGLE_PLACES_API_KEY` is valid and has quota — the France test returned empty, suggesting an issue.
2. Add OpenTripMap as secondary: `https://api.opentripmap.com/0.1/en/places/radius` — free, no billing, returns Wikipedia-sourced attractions.
3. Replace `CURATED_PLACES` fallback with LLM-generated POIs:
   ```
   Prompt: "List 8 must-visit attractions in {city} with: name, category, 
   typical_entry_cost_usd, visit_duration_hours, lat, lng. Use real places."
   ```
4. **Delete** entire `CURATED_PLACES` dictionary (~400 lines of static Iceland/Japan data).

---

### Geocoding / Map Pins

| Priority | Source | Free Tier | What it Returns |
|----------|--------|-----------|-----------------|
| **Primary** | **Google Geocoding** (existing key) | 10,000/mo | Precise lat/lng for any address |
| **Fallback** | **LocationIQ** | 5,000 req/day | Forward/reverse geocoding, free key |
| **Last resort** | **LLM-estimated** | Groq quota | Approximate lat/lng for major cities |

**Implementation** (`backend/app/agents/orchestrator.py`):
1. **Delete** hardcoded Iceland/Japan map pin generation (lines 842-859).
2. New function `_generate_dynamic_map_pins()`:
   - For each day in the itinerary, geocode the city name → lat/lng.
   - Use Google Geocoding API (already have key) or LLM knowledge for coordinates.
   - Generate pins for: arrival airport, each day's city, key attractions.
3. Pin types: `airport`, `hotel`, `attraction`, `restaurant`.

---

## Pipeline Bugs (Non-API)

### 1. UTF-8 Encoding Corruption
**Symptom**: "MusÃ©e" instead of "Musée" throughout output.
**Root Cause**: Double-encoding — UTF-8 bytes interpreted as Latin-1 in the pipeline.
**Fix**:
- In `groq_client.py`: ensure response `.text` or `.content` is decoded as UTF-8.
- In FastAPI JSON responses: use `ensure_ascii=False` in any `json.dumps()`.
- In orchestrator string concatenation: no `.encode().decode()` round-trips.
- **Test**: Run prompts for France (é), Germany (ü), Japan (東京), Thailand (กรุงเทพ).

### 2. Every Day Costs Exactly $100 ($20 × 5 activities)
**Symptom**: Flat pricing regardless of destination or activity type.
**Root Cause**: `_estimate_activity_cost()` uses a flat $20/activity.
**Fix**: Ask the LLM to estimate costs per activity when generating them:
```
In the activity generation prompt, add: "estimated_cost_usd" field.
The LLM already knows that Louvre entry = ~$17, Eiffel Tower = ~$30, 
a Paris café lunch = ~$15. Let it estimate.
```

### 3. Budget Rollup Categories Are Empty
**Symptom**: Grand total shows a number but category breakdown is null.
**Root Cause**: Rollup depends on flight/hotel data which is empty.
**Fix**: Once flights and hotels return dynamic data (even LLM-estimated), the budget agent can sum them. Add defensive logic: if a category has no data, use LLM-estimated range (e.g., "Hotels: ~$120-180/night for mid-range in Paris").

### 4. Hardcoded "Ring Road Vehicle Rental" & "KEF Airport Pickup"
**File**: `src/app/components/itinerary-display/itinerary-display.component.html`
**Fix**:
- Line 220: Change `<h3>Ring Road Vehicle Rental</h3>` → `<h3>Vehicle Rental</h3>` or use destination name.
- `getDestinationIata()`: return first destination IATA from itinerary data, not hardcoded "KEF".
- Only show vehicle rental section when `car_estimates.length > 0`.

### 5. Generic Cost-Saving Tips
**Root Cause**: Static list in orchestrator, same 3 tips for every destination.
**Fix**: Include in the Review Agent's LLM prompt:
```
"Generate 3 cost-saving tips specific to {destination}. 
Include local transit passes, museum passes, meal strategies, 
and booking timing advice. Each tip needs: title, description, 
estimated_savings."
```

### 6. Route Map Shows Iceland for Non-Iceland Trips
**Symptom**: Norway trip opens "Iceland Ring Road Route & GPS Pins" modal.
**Root Cause**: Route map component is hardcoded for Iceland Ring Road SVG.
**Fix**: Either generate a dynamic map from the itinerary's map_pins (once they're populated), or hide the route map when destination is not Iceland.

---

## New Features (Frontend Already Done)

### Feature 1: Origin City — Frontend ✅ / Backend ❌
**Frontend**: Origin city input with autocomplete already added to `ai-travel-planner.component.html`.
**Backend needed**:
1. Add `origin_city: Optional[str] = None` to `TravelConstraints` in `schemas.py`.
2. Add `origin_city` extraction to LLM prompt in `groq_client.py`.
3. Pass it through the API: add `origin_city` field to `/api/plan` request body in `main.py`.
4. Use in `flight_client.py` → `resolve_iata(origin_city)` instead of defaulting to "DEL"/"NAG".

### Feature 2: Travel Date — Frontend ✅ / Backend ❌
**Frontend**: Date picker already added to `ai-travel-planner.component.html`.
**Backend needed**:
1. Add `start_date: Optional[str] = None` to `TravelConstraints` in `schemas.py`.
2. Add `start_date` extraction to LLM prompt in `groq_client.py`.
3. Pass through API: add `start_date` field to `/api/plan` request body.
4. Use in flight search (departure_date), hotel search (arrival_date), and seasonal activity suggestions.

### Feature 3: Currency Consistency
**Current**: Backend defaults to `"INR"`, frontend defaults to `"USD"`.
**Fix**: Pass frontend's selected currency to backend with each request. Change `TravelConstraints.currency` default from `"INR"` to `"USD"`.

---

## Implementation Priority

| Phase | What | Effort | Impact |
|-------|------|--------|--------|
| **Phase 1** | UTF-8 fix + delete hardcoded KEF/Ring Road labels | 1 hour | Stops embarrassing bugs |
| **Phase 2** | Wire origin_city + start_date from frontend → backend | 2 hours | Flights use real origin |
| **Phase 3** | Replace flight fallback with LLM-estimated routes | 2 hours | Flights work for ANY destination |
| **Phase 4** | Replace hotel fallback with LLM-estimated hotels | 2 hours | Hotels work for ANY destination |
| **Phase 5** | Fix Google Places API call + add OpenTripMap fallback | 2 hours | POIs work for ANY destination |
| **Phase 6** | Dynamic map pins via geocoding | 1 hour | Map shows real locations |
| **Phase 7** | LLM-estimated activity costs + budget rollup | 1 hour | Realistic per-activity pricing |
| **Phase 8** | LLM-generated cost-saving tips + dynamic route map | 1 hour | Destination-specific tips |
| **Phase 9** | Integrate Kiwi Tequila API (flights) | 2 hours | Real flight prices |
| **Phase 10** | Integrate Booking.com Affiliate (hotels) | 2 hours | Real hotel availability |

**Total**: ~16 hours of implementation work.

---

## What to Delete

These static data structures should be **removed entirely** once LLM-based fallbacks are in place:

| File | What | Lines |
|------|------|-------|
| `hotel_client.py` | `CURATED_HOTELS` dict | ~180 lines |
| `hotel_client.py` | `KNOWN_DESTINATIONS` dict | ~35 lines |
| `google_places_client.py` | `CURATED_PLACES` dict | ~400 lines |
| `flight_client.py` | 4 hardcoded route cases in `_generate_realistic_fallback()` | ~200 lines |
| `orchestrator.py` | Hardcoded Iceland/Japan map pin generation | ~20 lines |
| `orchestrator.py` | Static `cost_saving_tips_v2` list | ~20 lines |

**Total**: ~855 lines of static data replaced by ~50 lines of LLM prompt templates.

---

## What Works Well (Keep These)

- LLM-generated **activities are excellent** — rich narratives, accurate attractions, good day pacing.
- **Strategic insight** and **why_this_plan** are thoughtful and destination-specific.
- **Neighborhoods** suggestions are accurate and useful.
- **Multi-region splitting** (4-3-3 days across cities) works perfectly.
- **5-agent pipeline** architecture is sound — just needs dynamic data sources.
- **Budget analysis** prose is smart.
- **Origin city + date picker UI** already implemented and tested (desktop + mobile).

---

## API Keys Needed

| API | Key Location | Status | Action |
|-----|-------------|--------|--------|
| Groq | `GROQ_API_KEY` in `.env` | ✅ Active | Keep |
| Google Places | `GOOGLE_PLACES_API_KEY` in `.env` | ⚠️ Verify quota | Test with a curl call |
| Kiwi Tequila | Not yet configured | ❌ Needed | Register at tequila.kiwi.com |
| OpenTripMap | Not yet configured | ❌ Optional | Register at opentripmap.io |
| Booking.com Affiliate | Not yet configured | ❌ Optional | Apply at booking.com/affiliate |
| LocationIQ | Not yet configured | ❌ Optional | Register at locationiq.com |
