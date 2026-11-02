# AI Travel Planner — Improvement Spec

> **Purpose**: Actionable spec for Antigravity to fix every gap found via live testing and code review.
> **Tested with**: `plan 10 days trip to france budget 10000$`
> **Date**: 2026-11-02

---

## Critical Bugs (Output is broken)

### 1. Flight Options Are Empty

**Symptom**: `flight_options: []` — no flights shown for France.

**Root Cause** (`backend/app/tools/flight_client.py`):
- `_generate_realistic_fallback()` (line 425) has only **4 hardcoded route cases**: India→Iceland, India→Australia, India→Japan, and a "Default Global" fallback.
- The Default Global case generates routes via DXB/DOH/SIN hubs — these are **not relevant for most destinations** (e.g. a US→France trip shouldn't route through Dubai).
- Origin always defaults to `"DEL"` (Delhi) in `resolve_iata()` (line 167) because there is no origin city field.

**Fix Required**:
- Make the fallback engine **destination-aware**: detect the destination's region and pick sensible hub airports. E.g. North America origins → direct or via major European hubs (LHR, CDG, FRA); Indian origins → via Middle East hubs; etc.
- Add **curated route templates** for at least: Europe (Paris CDG, Rome FCO, London LHR), Southeast Asia (Bangkok BKK, Singapore SIN), South America (Sao Paulo GRU), Africa (Johannesburg JNB, Cairo CAI).
- Use the user's **origin city** (see New Feature #1 below) instead of hardcoding DEL.

---

### 2. Hotel Options Are Empty for All 10 Days

**Symptom**: Every day in the itinerary has `hotel_options: []`.

**Root Cause** (`backend/app/tools/hotel_client.py`):
- `CURATED_HOTELS` dictionary only has entries for: **Reykjavik, Vik, Akureyri** (Iceland) and **Tokyo, Kyoto** (Japan).
- Paris IS in `KNOWN_DESTINATIONS` (has dest_id and coordinates) but has **no curated hotel entries**.
- Lyon, Nice, Marseille, Bordeaux — not in either dictionary.

**Fix Required**:
- Add **curated hotel entries** for all major tourist cities. At minimum:
  - **Europe**: Paris, Lyon, Nice, London, Rome, Florence, Barcelona, Madrid, Amsterdam, Berlin, Prague, Vienna, Zurich, Lucerne, Interlaken
  - **Asia**: Bangkok, Bali, Seoul, Singapore, Hong Kong, Delhi, Mumbai, Jaipur, Varanasi, Rishikesh
  - **Americas**: New York, Los Angeles, San Francisco, Cancun, Rio, Buenos Aires
  - **Oceania**: Sydney, Melbourne
- Each entry needs: hotel name, star rating, nightly rate (in USD), neighborhood, and coordinates.
- Hotels should have **realistic price variation** — not all the same rate. Include budget ($50-80), mid-range ($100-180), and premium ($200-400) tiers.

---

### 3. Map Pins Are Empty

**Symptom**: `map_pins: []` — the interactive map shows nothing.

**Root Cause** (`backend/app/agents/orchestrator.py`, lines 842-859):
- Map pin generation in `_draft_to_final()` is **hardcoded for Iceland and Japan only**.
- For Iceland: generates pins for Reykjavik, Vik, Akureyri, etc. with hardcoded lat/lng.
- For Japan: generates pins for Tokyo, Kyoto.
- **All other destinations get zero pins**.

**Fix Required**:
- Generate map pins **dynamically from the itinerary's cities/activities**.
- Each day already has a `city` field and activities with location names. Geocode those into lat/lng.
- Fallback: maintain a **coordinates lookup table** for 50+ major tourist cities worldwide, and use the city's coordinates as the pin for that day.
- Pin type should indicate: hotel (lodging), attraction (activity), transport (airport/station).

---

### 4. Places/POIs Are Empty for All Days

**Symptom**: Every day has `places: []`.

**Root Cause**: Google Places API is configured but either:
- Not being called for destinations outside the hardcoded set, OR
- The API key quota is exhausted / returning errors silently.

**Fix Required**:
- Verify `GOOGLE_PLACES_API_KEY` is valid and has quota.
- If Google Places is unreliable/costly, add **curated POI data** as fallback (similar to hotel/flight approach):
  - Top 10 attractions per major city with: name, category, typical visit duration, estimated cost, coordinates, opening hours.
- Ensure the places client is called for **every city** in the itinerary, not just hardcoded ones.

---

### 5. Budget Rollup Categories Are All Empty/Null

**Symptom**: `grand_total` shows $2,485 but individual category breakdowns (flights, hotels, activities, food, transport) are null/empty.

**Root Cause** (`backend/app/agents/orchestrator.py`):
- Budget rollup relies on data from flights, hotels, and activities.
- Since flights and hotels are empty, those categories can't be calculated.
- Activities each cost exactly $100/day (5 activities x $20 flat rate) regardless of destination.

**Fix Required**:
- `_estimate_activity_cost()` should use **destination-aware pricing**. Paris activities don't cost $20 each — Louvre entry is ~$17, Seine cruise is ~$15, Eiffel Tower is ~$30.
- Even when hotel/flight data is empty, the budget agent should **estimate** reasonable ranges based on destination and budget tier (budget/mid/luxury).
- Break down the grand total into categories with at least estimated ranges.

---

### 6. UTF-8 Encoding Corruption

**Symptom**: "MusÃ©e" instead of "Musée", "CafÃ©" instead of "Café" throughout the output.

**Root Cause**: Double-encoding issue — UTF-8 bytes being interpreted as Latin-1 somewhere in the pipeline (likely in the Groq LLM response parsing or JSON serialization).

**Fix Required**:
- Ensure all string handling uses UTF-8 consistently.
- Check `groq_client.py` response parsing — the LLM response content should be decoded as UTF-8.
- Check FastAPI response serialization — ensure `json.dumps()` uses `ensure_ascii=False`.
- Test with destinations that have diacritics: French (é, è, ê), German (ü, ö, ä), Spanish (ñ), Japanese (漢字), Thai (ภาษาไทย).

---

## Moderate Issues (Output is misleading)

### 7. Every Day Costs Exactly $100

**Symptom**: All 10 days show identical $100 daily cost (5 activities x $20 each).

**Root Cause**: `_estimate_activity_cost()` uses a **flat $20 per activity** regardless of destination, activity type, or budget level.

**Fix Required**:
- Create a cost estimation table by activity category and destination tier:
  - **Museum/Gallery**: $10-30 (varies by city)
  - **Guided Tour**: $30-80
  - **Food/Market**: $5-20
  - **Nature/Park**: $0-15
  - **Landmark**: $0-35
  - **Water Activity**: $20-60
- Factor in the user's budget level (budget vs. luxury) when estimating.

---

### 8. Hardcoded "Ring Road Vehicle Rental" & "KEF Airport Pickup"

**Symptom**: Frontend shows "Ring Road Vehicle Rental" heading and "KEF Airport Pickup" even for France trips.

**Root Cause** (`src/app/components/itinerary-display/itinerary-display.component.html`):
- Line 220: `<h3>Ring Road Vehicle Rental</h3>` is hardcoded.
- Line 223: `getDestinationIata()` returns `"KEF"` as default.

**Fix Required**:
- Change heading to dynamic: `"Vehicle Rental in {destination}"` or simply `"Vehicle Rental Options"`.
- `getDestinationIata()` should return the actual destination airport code from the itinerary data, not default to KEF.
- Only show the vehicle rental section when `car_estimates` is non-empty.

---

### 9. Cost-Saving Tips Are Generic

**Symptom**: Tips like "Book Flights 6-8 Weeks in Advance" are identical for every destination.

**Root Cause** (`backend/app/agents/orchestrator.py`, lines 883-899): `cost_saving_tips_v2` is a static list, not generated per-destination.

**Fix Required**:
- Make tips destination-specific. Examples for France:
  - "Buy a Paris Museum Pass (€62 for 4 days) — covers Louvre, Orsay, and 50+ museums"
  - "Use TGV OUIGO trains between cities — book 3 months early for €19 fares vs €80+ last-minute"
  - "Eat at boulangeries and marchés for lunch — a croque-monsieur + drink costs €8 vs €25 at a restaurant"

---

### 10. Origin Always Defaults to Delhi

**Symptom**: All flight routing assumes Delhi (DEL) as the origin.

**Root Cause**:
- `TravelConstraints` model (`backend/app/models/schemas.py`) has **no `origin_city` field**.
- `resolve_iata()` defaults to `"DEL"`.
- The LLM extraction prompt (`groq_client.py`, lines 145-187) does not ask for origin city.

**Fix Required**: See New Feature #1 below.

---

## New Features Required

### Feature 1: Origin City Input

**What**: Add an origin city field so flights, transit times, and routing are personalized.

**Backend Changes**:
1. Add `origin_city: Optional[str] = None` to `TravelConstraints` in `schemas.py`.
2. Update LLM extraction prompt in `groq_client.py` to extract origin city from the user's prompt.
3. Pass `origin_city` to `flight_client.py` → `resolve_iata()` instead of defaulting to DEL.
4. Update fallback routing logic to use origin's region for hub selection.

**Frontend Changes**:
1. Add an origin city input field above the Sample Blueprints row in `ai-travel-planner.component.html`.
2. Style: match the dark hero card theme (`bg-white/10`, `border-white/15`, Skyscanner blue accents).
3. Include an autocomplete dropdown with major airports/cities.
4. Pass origin city as part of the prompt or as a separate parameter to the backend.

---

### Feature 2: Travel Date Input

**What**: Add departure date so the planner can show seasonal advice, festival timing, and price estimates.

**Backend Changes**:
1. Add `start_date: Optional[str] = None` to `TravelConstraints` in `schemas.py`.
2. Update LLM extraction prompt to extract travel dates.
3. Use date context in:
   - `best_time_to_visit` — compare user's dates vs. optimal season.
   - Activity suggestions — seasonal events (Christmas markets in Dec, lavender fields in June).
   - Price estimates — peak vs. off-peak adjustments.

**Frontend Changes**:
1. Add a date picker input next to the origin city field.
2. Style: match the dark hero card theme.
3. Pass start date as part of the prompt or as a separate parameter.

---

### Feature 3: Currency-Aware Pricing Throughout

**What**: Backend currently defaults to INR (`currency` field in `TravelConstraints` defaults to `"INR"`). Frontend defaults to USD. These should be consistent.

**Fix**:
1. Change `currency` default in `TravelConstraints` from `"INR"` to `"USD"` (matching frontend default).
2. Or better: pass the frontend's selected currency to the backend with each request.
3. All cost estimates (activities, hotels, flights) should use the user's selected currency.

---

## Summary Priority Matrix

| Priority | Issue | Impact | Effort |
|----------|-------|--------|--------|
| P0 | Empty flights | Users see no flight options | Medium |
| P0 | Empty hotels | Users see no hotel options | Medium |
| P0 | Empty map pins | Map is blank | Medium |
| P0 | UTF-8 corruption | Text is garbled | Low |
| P1 | Empty places/POIs | No attraction details | Medium |
| P1 | Budget rollup empty | Cost breakdown missing | Low |
| P1 | Flat $100/day cost | Pricing feels fake | Low |
| P1 | Origin city feature | Always shows Delhi flights | Medium |
| P2 | Hardcoded Ring Road/KEF | Wrong labels for non-Iceland | Low |
| P2 | Generic saving tips | Tips not useful | Low |
| P2 | Travel date feature | No seasonal context | Medium |
| P2 | Currency mismatch | INR vs USD confusion | Low |

---

## What Works Well (Keep These)

- LLM-generated **activities are excellent** — rich narratives, accurate Paris/Lyon/Nice attractions, good day pacing.
- **Strategic insight** and **why_this_plan** are thoughtful and destination-specific.
- **Neighborhoods** suggestions are accurate and useful.
- **Best time to visit** advice is relevant.
- **Multi-region splitting** (4-3-3 days across Paris-Lyon-Nice) works perfectly.
- **Budget analysis** prose is smart (correctly identifies $10K as luxury tier).
- **5-agent pipeline UI** with progress stepper looks professional.
- **Sample blueprints** provide good starting points.
