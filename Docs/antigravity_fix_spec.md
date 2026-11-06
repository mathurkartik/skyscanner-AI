# Antigravity Fix Spec — Skyscanner AI Travel Planner

> **46 bugs. 4 priority tiers. 2 meta-bug sprints. ~26.5 hours total.**
> Generated from exhaustive 3-round audit (API tests + frontend template audit + competitor gap analysis).
> Each fix includes exact file, line number, what's wrong, and what to change.

---

## How to Use This Spec

1. **Work top-down by Sprint** — P0 first, then P1, P2, P3
2. **Meta-bug sprints** (Iceland Template Purge, Currency System) fix 16 bugs in 2 focused passes
3. **Each fix** has: Bug ID → File:Line → What's Wrong → What To Do
4. **Test after each sprint** using the edge case prompts in `backend/edge_case_round2_results.json`

---

## SPRINT 0: Critical Config Fix (~5 min)

### Bug #25 — Deprecated Gemini Model
- **File**: `backend/app/config.py:50`
- **What's wrong**: `gemini_model: str = "gemini-2.5-flash"` — this model is deprecated
- **Fix**: Change to `gemini_model: str = "gemini-2.5-flash-preview-05-20"` (or latest stable `gemini-2.5-flash` variant available)
- **Why first**: Everything else depends on the LLM working reliably

---

## SPRINT 1: Iceland Template Purge (~2 hours) — Fixes 6 bugs in one pass

> **Meta-bug**: The frontend has hardcoded Iceland demo content that displays on ALL trips regardless of destination.

### Bug #27 — Money-Saving Tips Are Iceland-Only
- **File**: `src/app/components/itinerary-display/itinerary-display.component.html:420-442`
- **What's wrong**: Tips section is hardcoded with Iceland content: "N1 fuel card", "Bónus supermarkets", "Blue Lagoon combo ticket"
- **Fix**: Replace the static HTML block with dynamic content from the API response. The backend `insights` object already has a `money_saving_tips` array. Bind to it:
  ```html
  <!-- REPLACE the static tips block (lines 420-442) with: -->
  <div *ngFor="let tip of itinerary.insights?.money_saving_tips">
    <p>{{ tip }}</p>
  </div>
  ```
- If `insights.money_saving_tips` is empty/null, hide the entire section with `*ngIf`

### Bug #28 — Smart Swap Hardcoded
- **File**: `src/app/components/itinerary-display/itinerary-display.component.html:493`
- **What's wrong**: "Hotel Kría → Guesthouse Carina in Vík saves ₹5,500/night" shown on every trip
- **Fix**: Either bind to a backend `smart_swaps` field (if it exists in the response), or hide this section entirely with `*ngIf="false"` until the backend supports it. Don't show Iceland hotel names on a Paris trip.

### Bug #29 — Driving Route Card Shown Unconditionally
- **File**: `src/app/components/itinerary-display/itinerary-display.component.html:585-614`
- **What's wrong**: "Route 1 Paved", "N1 Gas Station", "Bridge Alert: Single-lane bridges along glacial sands", "Verified sunlight hours: 07:30 - 18:45" shown on ALL trips, not just road trips
- **Fix**: Wrap the entire driving route card in `*ngIf="itinerary.constraints?.is_road_trip"`. Also replace hardcoded Iceland content with dynamic data from `transport_segments`.

### Bug #30 — Fallback Driving Time is Iceland-Specific
- **File**: `src/app/components/itinerary-display/itinerary-display.component.html:571-573`
- **What's wrong**: Fallback text "2.5 hrs to next stop" and "Route 1 Ring Highway" shown when no transport data exists
- **Fix**: Change fallback to generic text: "Drive to next destination" and hide the route name if not available. Better: use `transport_segments[i].route_description` if available.

### Bug #31 — Fallback Hotel is Iceland Hotel
- **File**: `src/app/components/itinerary-display/itinerary-display.component.html:808`
- **What's wrong**: When no hotel data, template shows "Hotel Kría ({{ city }})" at $220/nt
- **Fix**: Change fallback to generic: "Recommended stay in {{ city }}" with no price shown, or better, show "No hotel data available" and hide the price line.

### Bug #32 — Compare Blueprints Are Static
- **File**: `src/app/components/itinerary-display/itinerary-display.component.html:838-872`
- **What's wrong**: "Compare Blueprints" section always shows Japan, Sikkim, Switzerland regardless of trip destination
- **Fix**: Either hide this section entirely (`*ngIf="false"`) or generate contextually relevant comparisons based on `itinerary.constraints.destination_region`. Simplest fix: remove/hide the section.

---

## SPRINT 2: Currency System Overhaul (~4 hours) — Fixes 10 bugs in one pass

> **Meta-bug**: 4 conflicting currency behaviors across the stack:
> 1. Frontend sends hardcoded `'USD'` (line 147 of ai-travel-planner.component.ts)
> 2. Budget matrix uses `₹` for everything (lines 459-483 of itinerary-display HTML)
> 3. Transport costs use `$` for everything (line 176)
> 4. Flight prices multiply by hardcoded `83` for INR conversion (line 238)

### Step 1: Stop Hardcoding USD on Frontend
**Bug #1 — Frontend Sends Hardcoded USD**
- **File**: `src/app/components/ai-travel-planner/ai-travel-planner.component.ts:147`
- **What's wrong**: `this.plannerService.generatePlan(text, useStub, origin, date, 'USD')` — always sends USD regardless of user's prompt
- **Fix**: Remove the hardcoded `'USD'`. Let the backend extract currency from the user's prompt (it already does this — see `groq_client.py:158`). Change to:
  ```typescript
  this.plannerService.generatePlan(text, useStub, origin, date)
  ```
- **Also fix**: `src/app/services/travel-planner.service.ts:40` — remove the `currency` parameter entirely, or pass `null` so backend decides

### Step 2: Make Budget Matrix Currency-Aware
**Bug #2 — Budget Matrix Hardcodes ₹**
- **File**: `src/app/components/itinerary-display/itinerary-display.component.html:459,467,475,483`
- **What's wrong**: Four lines all hardcode `₹` symbol: `₹{{ budgetBreakdown.categories.stay }}` etc.
- **Fix**: Create a currency symbol pipe or helper. Use `itinerary.constraints.currency` to pick the symbol:
  ```typescript
  // In the component class:
  getCurrencySymbol(): string {
    const map: Record<string, string> = { 'USD': '$', 'EUR': '€', 'INR': '₹', 'GBP': '£', 'JPY': '¥', 'THB': '฿', 'AUD': 'A$' };
    return map[this.itinerary?.constraints?.currency] || '$';
  }
  ```
  Then replace all `₹{{ ... }}` with `{{ getCurrencySymbol() }}{{ ... }}`

### Step 3: Fix Transport Cost Symbol
**Bug #3 — Transport Costs Hardcode $**
- **File**: `src/app/components/itinerary-display/itinerary-display.component.html:176`
- **What's wrong**: `${{ segment.estimated_cost_usd }}` — hardcodes `$`
- **Fix**: Use the same `getCurrencySymbol()` helper: `{{ getCurrencySymbol() }}{{ segment.estimated_cost_usd }}`
- **Also rename** the field from `estimated_cost_usd` to `estimated_cost` in the backend if possible (separate task)

### Step 4: Remove Hardcoded ×83 Multiplier
**Bug #4 — Flight Price ×83 Conversion**
- **File**: `src/app/components/itinerary-display/itinerary-display.component.html:238`
- **What's wrong**: `₹{{ (flight.price * (itinerary.constraints.currency === 'INR' ? 1 : 83)) }}` — multiplies by 83 for non-INR, assumes all prices are INR
- **Fix**: The backend should return prices in the trip's currency. Remove the multiplication entirely:
  ```html
  {{ getCurrencySymbol() }}{{ flight.price | number:'1.0-0' }}
  ```
  If the Duffel API returns AUD (it does in sandbox), the backend `flight_client.py` should convert to the trip currency before returning.

### Step 5: Fix Hotel Price Symbol
**Bug #33 — Hotel Prices Hardcode $**
- **File**: `src/app/components/itinerary-display/itinerary-display.component.html:747`
- **What's wrong**: `${{ h.price_per_night }}/nt`
- **Fix**: `{{ getCurrencySymbol() }}{{ h.price_per_night }}/nt`

### Step 6: Fix Car Rental Static Prices
**Bug #34 — Car Rental Prices Are Static with ×83**
- **File**: `src/app/components/itinerary-display/itinerary-display.component.html:322-323,346,365,384`
- **What's wrong**: Hardcoded prices `$32/day`, `$45/day`, `$68/day` with `* 83` for INR conversion
- **Fix**: These should come from the API response. If no car rental data exists in the response, hide the car rental comparison section. Remove the `* 83` multiplier entirely.

### Step 7: Fix Backend Review Agent Currency
**Bug #14 — Review Agent Hardcodes $**
- **File**: `backend/app/agents/review.py:144`
- **What's wrong**: `message=f"Budget: ${total} vs limit ${budget}"` — hardcodes `$` in review messages
- **Fix**: Pass currency through to the review agent. Change to:
  ```python
  currency_sym = {"USD": "$", "EUR": "€", "INR": "₹", "GBP": "£"}.get(currency, "$")
  message=f"Budget: {currency_sym}{total} vs limit {currency_sym}{budget}"
  ```

### Step 8: Fix Duffel Flight Currency
**Bug #5 — Duffel API Returns AUD, No Conversion**
- **File**: `backend/app/tools/flight_client.py:307-313,377`
- **What's wrong**: No `currency` field in Duffel API request. Line 377 reads `total_currency` which returns AUD in sandbox.
- **Fix**: Add currency to the Duffel payload (Duffel API supports `currency` in offers request). In sandbox mode, at minimum convert AUD to the trip currency using a simple rate table, or flag the currency mismatch in the response.

### Step 9: Fix Backend Extraction Currency Defaults
**Bug #6 — Groq Extraction Defaults to USD Always**
- **File**: `backend/app/llm/groq_client.py:158`
- **What's wrong**: Currency defaults to "USD" unless explicitly INR/₹, EUR/€ — misses many currencies (THB, JPY, GBP, AUD, NZD, etc.)
- **Fix**: Expand the currency detection list to include all common travel currencies. Also add: `"THB": "THB", "baht": "THB", "¥": "JPY", "yen": "JPY", "£": "GBP", "pounds": "GBP", "A$": "AUD", "NZ$": "NZD", "kr": "SEK"` etc.

**Bug #7 — Gemini Extraction Same Issue**
- **File**: `backend/app/llm/gemini_client.py:196`
- **Fix**: Same expansion as Groq — keep both extraction prompts in sync.

---

## SPRINT 3: Map Pin System (~3 hours) — Fixes 3 bugs

### Bug #8 — Empty Coords Cache = All Pins Fall to Iceland
- **File**: `backend/app/agents/orchestrator.py:30-39,1132,1141`
- **What's wrong**: `_COORDS_CACHE = {}` is never populated. `_lookup_city_coords()` always returns `None`. All pins fall back to `(64.1466, -21.9426)` (Reykjavik, Iceland).
- **Fix — Option A (Quick, ~1 hour)**: Use a geocoding API. Add a function that calls Google Geocoding API (you already have a Google API key for Places):
  ```python
  import httpx

  async def _geocode_city(city: str) -> Tuple[float, float] | None:
      url = f"https://maps.googleapis.com/maps/api/geocode/json"
      params = {"address": city, "key": settings.google_api_key}
      async with httpx.AsyncClient() as client:
          resp = await client.get(url, params=params)
          data = resp.json()
          if data["results"]:
              loc = data["results"][0]["geometry"]["location"]
              _COORDS_CACHE[city] = (loc["lat"], loc["lng"])
              return (loc["lat"], loc["lng"])
      return None
  ```
  Replace `_lookup_city_coords(city) or (64.1466, -21.9426)` with `await _geocode_city(city) or (0, 0)` at lines 1132 and 1141.

- **Fix — Option B (Better, ~2 hours)**: Pre-populate `_COORDS_CACHE` with the top 200 travel cities. This avoids API calls and rate limits. Create a `city_coords.py` file:
  ```python
  CITY_COORDS = {
      "Paris": (48.8566, 2.3522),
      "Tokyo": (35.6762, 139.6503),
      "New York": (40.7128, -74.0060),
      "London": (51.5074, -0.1278),
      "Bali": (-8.3405, 115.0920),
      "Goa": (15.2993, 74.1240),
      # ... 200 more cities
  }
  ```

### Bug #35 — SVG Map Instead of Real Map
- **File**: `src/app/components/itinerary-display/itinerary-display.component.html:959`
- **What's wrong**: Map is a hand-drawn SVG with `viewBox="0 0 500 200"`, not an interactive map
- **Fix**: Replace the SVG section with a Google Maps embed or Leaflet.js map. Use `map_pins` data from the API response. The Angular component should:
  1. Install `@angular/google-maps` or `leaflet`
  2. Replace the SVG block (lines ~950-1020) with a `<google-map>` component
  3. Plot `itinerary.map_pins` as markers
  4. This is a bigger change — consider as a separate PR

### Bug #36 — Longitude Always Shows °W
- **File**: `src/app/components/itinerary-display/itinerary-display.component.html:1017`
- **What's wrong**: `{{ pin.lng.toFixed(3) }}°W` — hardcodes "W" for all longitudes. Eastern hemisphere cities (Tokyo, Bali, etc.) would show wrong direction.
- **Fix**: `{{ Math.abs(pin.lng).toFixed(3) }}°{{ pin.lng >= 0 ? 'E' : 'W' }}`
  (In Angular templates, you'd need a helper method since `Math` isn't directly available)

---

## SPRINT 4: Constraint Extraction Gaps (~3 hours) — Fixes 7 bugs

### Bug #9 — "Weekend" Not Parsed as Duration
- **File**: `backend/app/llm/groq_client.py:182`
- **What's wrong**: Duration extraction prompt says "e.g. 1 week = 7 days" but doesn't mention "weekend" = 2 days
- **Fix**: Add to the duration extraction prompt: `"weekend" = 2 days, "long weekend" = 3 days, "week" = 7 days, "fortnight" = 14 days`
- **Also fix in**: `backend/app/llm/gemini_client.py` (same extraction prompt)
- **Test**: "Weekend getaway to Pondicherry" should return `duration_days: 2`

### Bug #10 — Group Size Not Extracted
- **File**: `backend/app/models/schemas.py:78-97`
- **What's wrong**: `TravelConstraints` model has NO field for `group_size`, `travelers`, or `num_travelers`
- **Fix**: Add field to `TravelConstraints`:
  ```python
  group_size: int = Field(default=1, ge=1, le=20, description="Number of travelers")
  ```
- **Also update**: Groq extraction prompt (`groq_client.py:147-212`) to extract group size: `"group_size": <number of travelers, default 1>`
- **Also update**: Gemini extraction prompt (`gemini_client.py:185-214`) same addition
- **Also update**: Flight client (`flight_client.py:310`) to use `group_size` for passengers count instead of hardcoded single adult

### Bug #11 — Accessibility Needs Not Extracted
- **File**: `backend/app/models/schemas.py:78-97`
- **What's wrong**: No `accessibility_needs` field
- **Fix**: Add optional field:
  ```python
  accessibility_needs: Optional[List[str]] = Field(default=None, description="Accessibility requirements")
  ```
- Update extraction prompts in both Groq and Gemini clients to detect wheelchair, mobility, visual, hearing accessibility needs

### Bug #12 — Hindi/Mixed Language Crashes Server
- **File**: `backend/app/llm/groq_client.py` (extraction) and constraint parsing
- **What's wrong**: "Mujhe 7 din ka Kerala trip plan karo" returns HTTP 500: `int()` on empty string
- **Fix**: The extraction prompt needs to handle Hinglish. Add to system prompt: "The user may write in Hindi, Hinglish (Hindi+English), or other languages. Extract the same fields regardless of language." Also add input sanitization — if `int()` conversion fails, catch the ValueError and return a meaningful error.

### Bug #13 — Road Trip Country List Incomplete
- **File**: `backend/app/llm/groq_client.py:196-200`
- **What's wrong**: Road trip countries list is missing Sweden, Croatia, Rajasthan, Scotland, New Zealand South Island, etc.
- **Fix**: Expand the list, or better: change the logic to detect road trip from keywords ("road trip", "drive", "self-drive", "car rental", "route") rather than from a country list.

### Bug #44 — Duplicate Cities Crash (Ring Routes)
- **File**: `backend/app/models/schemas.py:110-118`
- **What's wrong**: `validate_cities_unique` raises `ValueError(f"Duplicate city: {city}")` — this crashes ring routes like "Munich → Vienna → Munich"
- **Fix**: Instead of raising an error, deduplicate silently OR allow the last city to match the first city (for return trips):
  ```python
  @field_validator('cities')
  @classmethod
  def validate_cities_unique(cls, v):
      if not v:
          return v
      # Allow ring routes (first == last)
      core = v[:-1] if len(v) > 1 and v[0] == v[-1] else v
      seen = set()
      deduped = []
      for city in core:
          if city.lower() not in seen:
              seen.add(city.lower())
              deduped.append(city)
      if len(v) > 1 and v[0] == v[-1]:
          deduped.append(v[0])
      return deduped
  ```

### Bug #46 — Budget Category Crash on Non-Standard Names
- **File**: `backend/app/agents/budget.py:230`
- **What's wrong**: `BudgetCategory(category=cat["category"], ...)` crashes when LLM returns creative category names like "sightseeing" instead of the strict `Literal["stay", "transport", "food", "activities", "buffer"]`
- **Fix**: Map non-standard categories to the closest standard one:
  ```python
  CATEGORY_MAP = {
      "accommodation": "stay", "hotel": "stay", "lodging": "stay", "housing": "stay",
      "flight": "transport", "train": "transport", "bus": "transport", "taxi": "transport", "car": "transport",
      "dining": "food", "meals": "food", "restaurant": "food", "eating": "food",
      "sightseeing": "activities", "tours": "activities", "entertainment": "activities", "attractions": "activities",
      "miscellaneous": "buffer", "other": "buffer", "emergency": "buffer", "tips": "buffer",
  }
  raw_cat = cat["category"].lower().strip()
  mapped_cat = CATEGORY_MAP.get(raw_cat, raw_cat)
  if mapped_cat not in ("stay", "transport", "food", "activities", "buffer"):
      mapped_cat = "activities"  # safe default
  ```

---

## SPRINT 5: Narrative & Content Quality (~3 hours) — Fixes 5 bugs

### Bug #15 — max_tokens=800 Truncates Narratives
- **File**: `backend/app/agents/orchestrator.py:1299`
- **What's wrong**: `max_tokens=800` for the narrative generation call. For 7+ day trips, this truncates heavily — 21/30 narratives missing on a 30-day trip.
- **Fix**: Scale max_tokens by trip duration:
  ```python
  token_budget = min(800 + (len(draft.days) * 100), 4000)
  content = await self.llm_client.chat_with_retry(
      messages=[...],
      max_tokens=token_budget
  )
  ```

### Bug #16 — Stub Fallback Has Generic Preferences
- **What's wrong**: When Groq token quota exhausts, stub responses return generic preferences like "Scenic landscapes", "Iconic landmarks", "Local cuisine", "Photography" regardless of what the user asked for (visible in tests 6, 7, 9 which all returned in 0.1s)
- **File**: Look for the stub/fallback generation code (likely in orchestrator or a fallback handler)
- **Fix**: At minimum, pass through the user's original preferences to the stub. Better: show the user an honest "LLM quota exhausted, using simplified response" message.

### Bug #37 — "Full 11-Day Journey Overview" Hardcodes 11
- **File**: `src/app/components/itinerary-display/itinerary-display.component.html:880`
- **What's wrong**: Hardcoded "Full 11-Day Journey Overview"
- **Fix**: `Full {{ itinerary.constraints.duration_days }}-Day Journey Overview`

### Bug #38 — India-Centric Placeholder
- **File**: `src/app/components/ai-travel-planner/ai-travel-planner.component.ts:55` (in the HTML template)
- **What's wrong**: Placeholder text mentions "₹3.5L budget" and "Nagpur" — India-specific
- **Fix**: Change to a more universal example: "7-day trip to Japan, $3000 budget, temples and food" or rotate through multiple examples

### Bug #39 — Error Message Dumps Raw JSON
- **File**: `src/app/services/travel-planner.service.ts:85`
- **What's wrong**: `JSON.stringify(error.error.detail)` — shows raw JSON to user on API error
- **Fix**: Parse the error and show a friendly message:
  ```typescript
  if (error.error?.detail?.message) {
    this.errorMessage = error.error.detail.message;
  } else if (typeof error.error?.detail === 'string') {
    this.errorMessage = error.error.detail;
  } else {
    this.errorMessage = 'Something went wrong. Please try again.';
  }
  ```

---

## SPRINT 6: Budget System Fixes (~3 hours) — Fixes 4 bugs

### Bug #17 — Budget Calibration Replaces Estimates Without Bounds
- **File**: `backend/app/agents/budget.py:63-170`
- **What's wrong**: `_calibrate_with_real_data()` replaces LLM estimates with raw Booking.com hotel prices without capping to the user's budget. A budget trip can show $400/night hotels.
- **Fix**: After calibration, clamp hotel prices to be within the per-night budget allocation:
  ```python
  max_per_night = budget_total / duration_days * 0.4  # 40% of daily budget for stay
  calibrated_price = min(real_price, max_per_night)
  ```

### Bug #18 — No Budget Grand Total Returned
- **What's wrong**: In 15/18 successful API tests, `budget_breakdown.grand_total` is `null`
- **File**: `backend/app/agents/budget.py` — the budget agent needs to compute and return the total
- **Fix**: After building the budget categories, sum them and set `grand_total`:
  ```python
  grand_total = sum(cat.amount for cat in categories)
  budget_breakdown.grand_total = grand_total
  budget_breakdown.within_budget = grand_total <= constraints.budget_total
  ```

### Bug #19 — Duffel Sandbox Returns Fake Airlines
- **File**: `backend/app/tools/flight_client.py`
- **What's wrong**: Duffel sandbox mode returns "Duffel Airways" — fake airline shown to users
- **Fix**: Add a flag or check. If in sandbox mode, either:
  - Add a disclaimer: "Sample flight data (prices may vary)"
  - Or substitute with realistic airline names based on the route (mapping function)
  - Long-term: Switch to Duffel production or add Amadeus/Skyscanner affiliate API

### Bug #45 — Flight Deeplink Goes to Skyscanner
- **File**: `backend/app/tools/flight_client.py:378`
- **What's wrong**: Generated deeplinks go to Skyscanner search URL. For a portfolio project this is fine, but should be disclosed.
- **Fix**: Low priority. Either keep as-is (it's a Skyscanner PM portfolio piece) or add a note in the UI: "Search on Skyscanner"

---

## SPRINT 7: Frontend Polish (~3 hours) — Fixes 6 bugs

### Bug #40 — Timeout Message References "Free-Tier"
- **File**: `src/app/services/travel-planner.service.ts:80`
- **What's wrong**: Message says "free-tier servers" and "cold start" — exposes infrastructure details
- **Fix**: Change to: "Our servers are warming up. This can take up to 60 seconds for the first request."

### Bug #41 — No Loading State for Long Requests
- **What's wrong**: 45-150 second API calls with no progress indication
- **File**: `src/app/components/ai-travel-planner/` (component)
- **Fix**: Add a multi-stage loading indicator:
  - 0-10s: "Understanding your trip..."
  - 10-30s: "Finding the best destinations..."
  - 30-60s: "Comparing flights and hotels..."
  - 60s+: "Almost there — putting it all together..."

### Bug #42 — Mobile Responsiveness Issues
- **File**: `src/app/components/itinerary-display/itinerary-display.component.html` + CSS
- **What's wrong**: Budget matrix and flight cards overflow on mobile viewports
- **Fix**: Add responsive CSS. Budget grid should stack to single column on mobile. Flight cards should use horizontal scroll or stack.

### Bug #43 — No Share/Export Functionality
- **What's wrong**: No way to save, share, or export the generated itinerary
- **Fix**: Add a "Download PDF" or "Copy to Clipboard" button. Simplest: add a "Copy Link" that generates a shareable URL with the itinerary ID, or a "Print" button that opens print dialog.

### Bug #20 — Brotli Decompression Error on Large Responses
- **What's wrong**: Test 3 (wheelchair Japan, 10 days) crashed with brotli decoder error — response too large
- **File**: Backend response compression / httpx client config
- **Fix**: Add `Accept-Encoding: gzip, deflate` header (avoiding brotli) in the API, or increase response size limits. Also investigate if the response can be streamed.

### Bug #26 — No Rate Limit Feedback to User
- **What's wrong**: When Groq quota exhausts (100k tokens/day), the app silently degrades to stub responses with no user notification
- **File**: Backend health endpoint + frontend
- **Fix**: The health endpoint already tracks quota. When quota is low, return a warning in the API response that the frontend can display: "Running on simplified mode — some features may be limited"

---

## SPRINT 8: Remaining P2/P3 Issues (~5 hours) — Fixes 5 bugs

### Bug #21 — No Visa/Entry Requirements
- **What's wrong**: Competitors show visa info; this app doesn't
- **File**: Backend `insights` generation
- **Fix**: Add visa info to the LLM prompt for the review/insights agent. Include: "Does destination X require a visa for travelers from origin Y?"

### Bug #22 — No Weather/Season Awareness
- **What's wrong**: No seasonal warnings (monsoon, extreme cold, etc.)
- **Fix**: Add to the destination agent prompt: "Consider the travel dates and mention weather conditions or seasonal factors"

### Bug #23 — No Local Transport Info
- **What's wrong**: No info about metro, buses, ride-hailing within cities
- **Fix**: Add to day-level output: "local_transport_tip" field with info like "Use Grab for rides" or "Get a Tokyo metro pass"

### Bug #24 — Activities Lack Operating Hours/Prices
- **What's wrong**: Activities listed without practical details
- **Fix**: Google Places API already returns opening hours and price levels. Include these in the activity objects returned by the destination agent.

### Bug #39b — 3-Pillar Validation Error Messages Not Localized
- **What's wrong**: Error messages are in English only, technical format
- **Fix**: The 400 responses already have decent messages. Low priority — keep as-is for now.

---

## Priority Summary

| Sprint | Bugs Fixed | Time | Impact |
|--------|-----------|------|--------|
| Sprint 0: Config | 1 | 5 min | Unblocks everything |
| Sprint 1: Iceland Purge | 6 | 2 hrs | Removes fake content from all trips |
| Sprint 2: Currency System | 10 | 4 hrs | Fixes all money display issues |
| Sprint 3: Map Pins | 3 | 3 hrs | Maps actually work |
| Sprint 4: Constraint Extraction | 7 | 3 hrs | More prompts work correctly |
| Sprint 5: Narratives/Content | 5 | 3 hrs | Better output quality |
| Sprint 6: Budget System | 4 | 3 hrs | Budget accuracy |
| Sprint 7: Frontend Polish | 6 | 3 hrs | UX improvements |
| Sprint 8: P2/P3 Polish | 5 | 5 hrs | Competitor parity |
| **Total** | **46** | **~26.5 hrs** | |

---

## Recommended Order for Interview Demo Impact

If you only have time for **Sprints 0-2** (~6 hours), you fix **17 bugs** and eliminate the two most embarrassing issues:
1. No more Iceland content on Paris trips
2. No more ₹ symbols on USD trips

Add **Sprint 3** (~3 more hours) and the map works = **20 bugs fixed, ~9 hours**.

Add **Sprint 4** (~3 more hours) and edge cases stop crashing = **27 bugs fixed, ~12 hours**.

That's the critical path: **27 bugs in 12 hours** covers every P0 and most P1s.

---

## Test Prompts to Verify Fixes

After each sprint, test with these prompts:

1. **Currency**: "7-day trip to Paris, €3000 budget" → should show € everywhere
2. **Iceland purge**: "5-day Tokyo trip, $2000" → no Iceland content, no N1 fuel cards
3. **Map pins**: "10-day Georgia trip" → pins at Tbilisi (41.7°N), not Reykjavik
4. **Weekend**: "Weekend getaway to Pondicherry from Chennai, ₹5000" → should parse as 2 days
5. **Group**: "Goa trip for 6 friends" → should show 6 passengers on flights
6. **Hindi**: "Mujhe 7 din ka Kerala trip plan karo" → should not crash (HTTP 500)
7. **Ring route**: "Munich → Vienna → Munich road trip" → should not crash on duplicate city
8. **Long trip**: "30-day Southeast Asia backpacking, $3000" → narratives for all 30 days
