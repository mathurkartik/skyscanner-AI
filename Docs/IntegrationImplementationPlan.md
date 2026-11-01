# Integration Implementation Plan

## Skyscanner AI Travel Planner — Standalone

Reference: `IntegrationProblemStatement.md`, `IntegrationArchitecture.md`

**Key principle:** The backend lives at `skyscanner/backend/` and runs independently. Agent pipeline code is replicated from `M4/backend/` as reference, then adapted. Zero runtime dependency on M4.

---

## Phase 0 — Scaffold Backend & Connectivity

**Goal:** Create the `skyscanner/backend/` folder structure, replicate the core pipeline from M4, and establish connectivity with the Angular frontend.

**Tasks:**

1. **Create `skyscanner/backend/` folder structure:**
   ```
   skyscanner/backend/
   ├── app/
   │   ├── __init__.py
   │   ├── main.py              # FastAPI app + CORS + health
   │   ├── config.py            # Settings with all API keys
   │   ├── api/
   │   │   ├── __init__.py
   │   │   └── routes.py        # POST /api/plan, GET /health
   │   ├── agents/
   │   │   ├── __init__.py
   │   │   ├── orchestrator.py
   │   │   ├── trip_structuring.py
   │   │   ├── destination.py
   │   │   ├── logistics.py
   │   │   ├── budget.py
   │   │   └── review.py
   │   ├── models/
   │   │   ├── __init__.py
   │   │   └── schemas.py       # All Pydantic models
   │   ├── tools/
   │   │   ├── __init__.py
   │   │   └── router.py        # ToolRouter with price_band, etc.
   │   ├── llm/
   │   │   ├── __init__.py
   │   │   ├── groq_client.py   # Groq LLM client
   │   │   └── cache.py         # Response cache
   │   └── utils/
   │       ├── __init__.py
   │       └── observability.py
   ├── requirements.txt
   ├── .env.example
   └── .env
   ```

2. **Replicate core files from M4** (copy and adapt):
   - `main.py` — FastAPI app, CORS middleware (allow `http://localhost:4200`), health endpoint
   - `config.py` — `Settings(BaseSettings)` with `groq_api_key`, `rapidapi_key`, `google_places_api_key`, `cors_origins`
   - `api/routes.py` — `POST /api/plan`, `GET /health`
   - `models/schemas.py` — all Pydantic models (`PlanRequest`, `PlanResponse`, `TravelConstraints`, `FinalItinerary`, `DayItinerary`, `BudgetBreakdown`, etc.)
   - `agents/` — all 6 agent files (orchestrator, trip_structuring, destination, logistics, budget, review)
   - `tools/router.py` — `ToolRouter` with `price_band()`, `geo_estimate()`, `fx_convert()`
   - `llm/groq_client.py` — Groq LLM client with rate limiting and model fallback
   - `llm/cache.py` — LLM response cache
   - `requirements.txt` — Python dependencies (fastapi, uvicorn, pydantic-settings, httpx, groq)

   **Reference:** Read each M4 file at `@M4/backend/app/...` and replicate it into `skyscanner/backend/app/...`. Adapt imports (no M4 references). Simplify where possible — remove any M4-specific features not needed for the Skyscanner integration.

3. **Create `.env.example` and `.env`:**
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   RAPIDAPI_KEY=
   GOOGLE_PLACES_API_KEY=
   CORS_ORIGINS=http://localhost:4200
   ```

4. **Create Angular proxy and environment files:**
   - Create `skyscanner/proxy.conf.json` pointing to `http://localhost:8000`
   - Register `"proxyConfig": "proxy.conf.json"` in `angular.json` serve options
   - Create `skyscanner/src/environments/environment.ts` with `apiBaseUrl: 'http://localhost:8000'`
   - Create `skyscanner/src/environments/environment.prod.ts` for production builds
   - Add `provideHttpClient(withFetch())` to `skyscanner/src/app/app.config.ts`

5. **Verify connectivity:**
   - Start backend: `cd skyscanner/backend && uvicorn app.main:app --reload --port 8000`
   - Start Angular: `cd skyscanner && ng serve`
   - Test: Angular can reach `GET /health` and `POST /api/plan` (stub response is fine)

6. **Verify the replicated pipeline works:**
   - Test: `POST /api/plan` with a simple prompt returns a structured itinerary (LLM-generated, no real API data yet)

**Exit criteria:** `skyscanner/backend/` runs standalone, Angular proxies to it, and `POST /api/plan` returns a basic LLM-generated itinerary.

**Dependencies:** None

**Estimated effort:** Large (replicating the full pipeline) — but it's mostly copy-and-adapt, not new logic

---

## Phase 1 — RapidAPI Flight Client

**Goal:** Create a Python client that calls RapidAPI Skyscanner for real flight data, inside `skyscanner/backend/`.

**Tasks:**

1. **Create `skyscanner/backend/app/tools/flight_client.py`**
   - `search_flights(origin, destination, departure_date, return_date, cabin_class, adults)` → `list[RealFlightOffer]`
   - Single GET request to `skyscanner44.p.rapidapi.com/search` — no session tokens, no polling
   - Auth: `x-rapidapi-key` + `x-rapidapi-host` headers from `Settings.rapidapi_key`
   - Transform response into `RealFlightOffer` Pydantic models (reuse field mapping from Angular's `skyscanner-api.service.ts` `transformSkyscannerResponse()`)

2. **City name → IATA code resolution**
   - Hardcoded dict for demo routes: `{"Reykjavik": "KEF", "Tokyo": "NRT", "Zurich": "ZRH", "Nagpur": "NAG", ...}`
   - LLM fallback: ask the LLM to resolve unknown city names to IATA codes
   - Can expand later by importing from `airports.data.ts`

3. **Caching:** In-memory dict keyed by `(origin + destination + dates)`, TTL 1 hour. Same pattern as `ToolRouter._cache`.

4. **Fallback:** If RapidAPI unavailable or key not set, fall back to `ToolRouter.price_band()` + LLM estimates.

5. **Write tests** with mocked RapidAPI responses.

**Exit criteria:** `FlightClient.search_flights("NAG", "KEF", "2026-12-01", "2026-12-11")` returns real flight offers with airline names, prices, and durations.

**Dependencies:** Phase 0

**Estimated effort:** Medium

---

## Phase 2 — Booking.com Hotel Client

**Goal:** Create a Python client that calls Booking.com RapidAPI for real hotel data.

**Tasks:**

1. **Create `skyscanner/backend/app/tools/hotel_client.py`**

   **Step 1 — Resolve destination:**
   - `search_destination(query: str)` → `{ dest_id, dest_type, label }`
   - `GET booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination?query=Reykjavik`
   - Cache `dest_id` lookups for 24 hours (city→dest_id is stable)

   **Step 2 — Search hotels:**
   - `search_hotels(dest_id, dest_type, arrival_date, departure_date, adults, room_qty)` → `list[RealHotelOffer]`
   - `GET booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels?dest_id=...&arrival_date=...`
   - Returns: hotel name, price/night, star rating, guest score, reviews, photos, address, amenities

   **Alternative — by coordinates:**
   - `search_hotels_by_coords(lat, lng, arrival_date, departure_date, adults)` → `list[RealHotelOffer]`
   - `GET booking-com15.p.rapidapi.com/api/v1/hotels/searchHotelsByCoordinates?latitude=...`
   - Useful when we have coordinates from Google Places but no dest_id

2. **Caching:** 1-hour TTL for hotel search results, 24-hour TTL for dest_id lookups.

3. **Fallback:** If unavailable, fall back to mock hotel data + LLM-generated names.

4. **Free tier management:** ~100-500 requests/month. Pre-warm demo routes. Cache aggressively.

5. **Write tests** with mocked Booking.com responses.

**Exit criteria:** `HotelClient.search_hotels(dest_id, ...)` returns real hotel offers with names, prices, ratings, and images for Reykjavik, Vik, and Akureyri.

**Dependencies:** Phase 0

**Estimated effort:** Medium

**Note:** Phase 1 and Phase 2 can run in parallel — they are independent API clients using the same RapidAPI key.

---

## Phase 3 — Google Places API Client

**Goal:** Create a Python client for Google Places API to get real attraction ratings, opening hours, and photos.

**Tasks:**

1. **Create `skyscanner/backend/app/tools/google_places_client.py`** with methods:

   | Method | Google API | Returns |
   |--------|-----------|---------|
   | `search_nearby(lat, lng, radius_m, type)` | Places Nearby Search | List of places with name, place_id, rating, location |
   | `get_place_details(place_id)` | Place Details | Full details: name, rating, review_count, opening_hours, types, photos, address |
   | `search_text(query, location_bias)` | Text Search | Places matching a query near a location |

2. **Caching:** 24-hour TTL. Keyed by `(place_id)` for details, `(lat, lng, radius, type)` for nearby searches.

3. **Fallback:** Return empty list if API unavailable or key not set. The LLM still generates attraction recommendations.

4. **Write tests** with mocked Google Places responses.

**Exit criteria:** Can get top-rated attractions near Reykjavik (64.1466°N, 21.9426°W), Vik, and Akureyri with real ratings and opening hours.

**Dependencies:** Phase 0

**Estimated effort:** Medium

**Note:** Phases 1, 2, and 3 can all run in parallel.

---

## Phase 4 — Extend Data Models

**Goal:** Add new Pydantic models for real API data and extend existing models to carry it alongside LLM-generated content.

**Tasks:**

1. **Add new models** to `skyscanner/backend/app/models/schemas.py`:
   - `RealFlightOffer` — airline, flight_number, price, currency, duration_minutes, stops, stop_cities, departure, arrival, deeplink
   - `RealHotelOffer` — name, price_per_night, currency, star_rating, guest_rating, review_count, neighborhood, image_url, deeplink, amenities
   - `CarEstimate` — supplier, vehicle_name, category, price_per_day, total_price, currency, seats, transmission, `is_estimate: bool = True`
   - `PlaceInfo` — name, rating, review_count, types, opening_hours, coordinates, photo_url, description
   - `MapPin` — label, lat, lng, day_number, pin_type ("overnight" | "attraction" | "transit")
   - `CostSavingTip` — title, description

2. **Extend `DayItinerary`** — add optional fields:
   - `hotel_options: list[RealHotelOffer] = []`
   - `places: list[PlaceInfo] = []`
   - `driving_time_to_next: Optional[str] = None`

3. **Extend `FinalItinerary`** — add optional fields:
   - `flight_options: list[RealFlightOffer] = []`
   - `car_estimates: list[CarEstimate] = []`
   - `map_pins: list[MapPin] = []`
   - `cost_saving_tips_v2: list[CostSavingTip] = []` — named `_v2` to avoid conflict with existing `cost_optimization_tips: List[str]`

4. **All new fields must have defaults** (`= []` or `= None`) so the pipeline works even before real data sources are wired in.

5. **Write test fixtures** — sample JSON with real data for serialization/deserialization tests.

**Exit criteria:** Extended models serialize/deserialize correctly. Existing pipeline still works.

**Dependencies:** Phase 1, Phase 2, Phase 3 (model shapes need to match API response transformations)

**Estimated effort:** Medium

---

## Phase 5 — Wire Agents to Use Real Data

**Goal:** Connect the real API clients into the agent pipeline so agents use real data instead of LLM estimates.

**This is the core integration phase.**

**Tasks:**

1. **Orchestrator Agent** (`orchestrator.py`):
   - After extracting constraints, resolve city names → IATA codes (hardcoded map + LLM fallback)
   - Resolve city names → Booking.com `dest_id` via `HotelClient.search_destination()`
   - Pass resolved IDs to worker agents along with constraints
   - During merge: attach `hotel_options` per day, `flight_options`, `car_estimates`, `map_pins`, `cost_saving_tips_v2`

2. **Logistics Agent** (`logistics.py`):
   - Call `FlightClient.search_flights()` for flights (origin → destination, and return)
   - Call `HotelClient.search_hotels()` for each overnight stop (using dest_id or coordinates)
   - Generate `CarEstimate` using `ToolRouter.price_band()` + LLM knowledge if road trip
   - Return real offers alongside LLM-generated logistics plan

3. **Destination Research Agent** (`destination.py`):
   - After LLM generates activity recommendations, call `GooglePlacesClient.search_text()` for each place
   - Merge real data: replace LLM-estimated ratings with Google Places ratings, add hours, photos
   - LLM still curates which places to recommend and crowd avoidance

4. **Budget Agent** (`budget.py`):
   - Receive real flight + hotel prices from Logistics agent
   - Calculate actual totals: real hotel × nights, real flight prices
   - Car/food/activities stay calibrated LLM estimates
   - `suggested_swaps` uses cheaper hotel alternatives from same Booking.com results

5. **Review Agent** (`review.py`):
   - Validate budget using real flight + hotel totals + calibrated estimates

**Important:** Keep existing LLM planning logic intact. APIs INFORM and ENRICH, not replace. The LLM curates "which temples are quiet" — the APIs provide "how much does the hotel actually cost."

**Exit criteria:** `POST /api/plan` with "Plan an 11-day Iceland road trip, ₹3.5L budget" returns itinerary with real hotel names/prices, real flight prices, and real attraction ratings.

**Dependencies:** Phase 4

**Estimated effort:** Large — touches all agents

---

## Phase 6 — TypeScript Models in Angular

**Goal:** Create TypeScript interfaces matching the backend response.

**Tasks:**

1. Read the models from `skyscanner/backend/app/models/schemas.py`
2. Create `skyscanner/src/app/models/travel-planner.model.ts` with matching interfaces:
   - `PlanResponse`, `FinalItinerary`, `DayItinerary`, `BudgetBreakdown`, `BudgetCategory`
   - `RealFlightOffer`, `RealHotelOffer`, `CarEstimate`, `PlaceInfo`
   - `MapPin`, `CostSavingTip`, `TravelConstraints`, `ReviewStatus`

**Exit criteria:** TypeScript interfaces compile and match the backend response JSON.

**Dependencies:** Phase 4

**Estimated effort:** Small

---

## Phase 7 — Angular API Service

**Goal:** Create an Angular service that calls the backend.

**Tasks:**

1. Create `skyscanner/src/app/services/travel-planner.service.ts`:
   - `generatePlan(prompt: string): Observable<PlanResponse>` — POST /api/plan
   - `checkHealth(): Observable<any>` — GET /health
2. 90-second timeout (LLM pipeline + API calls takes 30-60s)
3. Error mapping: network errors, validation errors, timeout

**Exit criteria:** Service can call the backend and receive a real itinerary response.

**Dependencies:** Phase 6

**Estimated effort:** Small

---

## Phase 8 — "Plan with AI" Tab in Navbar

**Goal:** Add a "Plan with AI" pill button and switch the AI planner from a modal overlay to a full page tab.

**Tasks:**

1. **Add pill button** in `navbar.component.html` after Cars pill:
   - Label: "Plan with AI", Icon: sparkle SVG
   - Style: same as Flights/Stays/Cars pills (`bg-[#072044]` inactive, `bg-[#0062e3]` active, `rounded-full`)

2. **Fix tab behavior** — three places currently shortcut to the modal:

   | File | Current Behavior | New Behavior |
   |------|-----------------|-------------|
   | `navbar.component.ts` | `setTab('ai')` calls `flightService.openAiPlanner()`, returns early | Emit `'ai'` via `tabChanged.emit('ai')` |
   | `app.ts` | `onTabChange('ai')` calls `flightService.openAiPlanner()`, returns early | `this.currentTab.set('ai')` like other tabs |
   | `home-feed.component.ts` | `openTab('ai')` calls `flightService.openAiPlanner()` directly | `this.navigateTab.emit('ai')` |

3. **Update `app.html`:** Add `@if (currentTab() === 'ai')` section, remove modal overlay block

4. **Clean up `flight.service.ts`:** Remove `showAiPlannerModal`, `openAiPlanner()`, `closeAiPlanner()`

**Exit criteria:** "Plan with AI" pill appears in navbar; clicking shows the planner as a full page.

**Dependencies:** None — can run in parallel with backend phases

**Estimated effort:** Medium

---

## Phase 9 — Rewrite AI Planner Component

**Goal:** Replace the fake AI planner with a real one that calls the backend.

**Tasks:**

1. Rewrite `ai-travel-planner.component.ts`:
   - Full page layout (not modal)
   - Call `TravelPlannerService.generatePlan()` instead of setTimeout chains
   - Remove all hardcoded agent steps and Japan-only output

2. Input section: textarea with suggestion chips

3. Loading state: "Planning your trip..." with progress message

4. Error state: message + retry button

5. Success state: display itinerary via child `ItineraryDisplayComponent`

**Exit criteria:** User types prompt, sees loading, then sees real itinerary.

**Dependencies:** Phase 7, Phase 8

**Estimated effort:** Medium

---

## Phase 10 — Itinerary Display (Gemini-style Output)

**Goal:** Render the full AI-generated itinerary with real data.

**Tasks:**

Create `itinerary-display.component.ts` with sections:

1. Trip header + summary
2. Budget breakdown table (real prices for flights/hotels, estimates for car/food/activities)
3. Day-by-day cards (hotel options with Booking.com data, attractions with Google Places ratings)
4. Remaining days table (compact)
5. Google Maps embed with route pins
6. Cost-saving tips
7. Flight summary + "Search Flights" button, car estimate summary

**Style:** Skyscanner design language — dark navy `#02122c`, blue CTAs `#0062e3`, Tailwind. Responsive.

**Exit criteria:** Full itinerary displays with real hotel names, prices, ratings, and real attraction data.

**Dependencies:** Phase 9

**Estimated effort:** Large

---

## Phase 11 — Booking Integration

**Goal:** Connect itinerary items to real booking pages.

**Tasks:**

1. "Search Flights" → open RapidAPI flight deeplink or call `FlightService.executeSearch()` with IATA codes
2. "Book Hotel" → open Booking.com hotel deeplink from API response
3. Fallback (no deeplinks): pre-fill existing app search forms

**Exit criteria:** User can click through from itinerary to real booking/search pages.

**Dependencies:** Phase 10

**Estimated effort:** Small-Medium

---

## Phase 12 — Polish and Demo Prep

**Goal:** Make the integration demo-reliable for the Skyscanner PM interview.

**Tasks:**

1. Loading skeletons during API wait
2. Error states: backend down, timeout, no results
3. Retry button on failures
4. Pre-cache popular routes (Iceland, Japan, Switzerland) for demo reliability
5. Test with diverse prompts: short trips, road trips, multi-city, different budgets/currencies
6. Google Maps embed with correct pins
7. Responsive: mobile viewport
8. Final demo script

**Exit criteria:** Smooth end-to-end demo — prompt → real itinerary → click to book.

**Dependencies:** Phase 11

**Estimated effort:** Medium

---

## Dependency Graph

```
Phase 0 (Scaffold Backend + Replicate Pipeline)
  ├── Phase 1 (Flight Client) ─────┐
  ├── Phase 2 (Hotel Client) ──────┤
  ├── Phase 3 (Google Places) ─────┤
  │                                ├── Phase 4 (Extend Models) → Phase 5 (Wire Agents)
  │                                │                                    ↓
  │                                │                            Phase 6 (TS Models)
  │                                │                            Phase 7 (Angular Service)
  │                                │                                    ↓
  └── Phase 8 (AI Tab in Navbar) ──────────────────────────── Phase 9 (Rewrite Planner)
                                                                       ↓
                                                                Phase 10 (Itinerary Display)
                                                                       ↓
                                                                Phase 11 (Booking)
                                                                       ↓
                                                                Phase 12 (Polish)
```

**Parallel tracks:**
- **Backend track:** Phase 0 → Phase 1 + 2 + 3 (parallel) → Phase 4 → Phase 5
- **Frontend track:** Phase 0 → Phase 8 (can start immediately after Phase 0)
- **Bridge:** Phase 6 + 7 connect backend to frontend

---

## Effort Summary

| Phase | Effort | Can Parallelize With |
|-------|--------|---------------------|
| Phase 0 — Scaffold Backend | Large | — |
| Phase 1 — Flight Client | Medium | Phase 2, 3 |
| Phase 2 — Hotel Client | Medium | Phase 1, 3 |
| Phase 3 — Google Places | Medium | Phase 1, 2 |
| Phase 4 — Extend Models | Medium | Phase 8 |
| Phase 5 — Wire Agents | Large | Phase 8 |
| Phase 6 — TS Models | Small | — |
| Phase 7 — Angular Service | Small | — |
| Phase 8 — AI Tab | Medium | Phases 1-5 |
| Phase 9 — Rewrite Planner | Medium | — |
| Phase 10 — Itinerary Display | Large | — |
| Phase 11 — Booking | Small-Medium | — |
| Phase 12 — Polish | Medium | — |

---

## Prerequisites — API Keys

Before starting Phases 1-3 (not needed for Phase 0):

1. **Groq API key** — you already have this. Put it in `skyscanner/backend/.env`
2. **RapidAPI key** — one key covers both Skyscanner flights and Booking.com hotels. Sign up at https://rapidapi.com, subscribe to both APIs (free tier). Self-service, instant.
3. **Google Places API key** — get from https://console.cloud.google.com. Enable Places API. Free tier: ~5,000 requests/month.

---

## Phase 0 Note — Previous M4 Changes

Phase 0 was previously attempted against `M4/backend/` (added CORS origin, env vars to M4's config.py). Those changes are harmless but unnecessary — the Skyscanner project now has its own backend. The M4 backend changes can stay (they don't break anything) or be reverted — your choice. The Angular frontend changes from that attempt are no longer present and need to be recreated as part of this Phase 0.
