# Skyscanner AI Travel Planner — Integration Prompts (Standalone)

These are the prompts to give (in order) to build the standalone AI travel planner backend inside `skyscanner/backend/` and integrate it with the Skyscanner Angular frontend.

**Key principle:** The backend at `skyscanner/backend/` is a standalone FastAPI server. The M4 project at `M4/backend/` is reference code only — read it to understand the agent pipeline structure, then replicate and adapt into `skyscanner/backend/`. Zero runtime dependency on M4.

---

## Prompt 1 — Problem Statement (ALREADY DONE)

> Already created: `skyscanner/Docs/IntegrationProblemStatement.md`

---

## Prompt 2 — Architecture Document (ALREADY DONE)

> Already created: `skyscanner/Docs/IntegrationArchitecture.md`

---

## Prompt 3 — Implementation Plan (ALREADY DONE)

> Already created: `skyscanner/Docs/IntegrationImplementationPlan.md`

---

## Prompt 4 — Implement Phase 0 (Scaffold Backend & Connectivity)

> Implement Phase 0 from `@skyscanner/Docs/IntegrationImplementationPlan.md`.
>
> Create a standalone FastAPI backend at `skyscanner/backend/` by replicating the multi-agent pipeline from `@M4/backend/`. This is a standalone copy — zero imports from M4 at runtime.
>
> **Step 1 — Scaffold the folder structure:**
> ```
> skyscanner/backend/
> ├── app/
> │   ├── __init__.py
> │   ├── main.py
> │   ├── config.py
> │   ├── api/
> │   │   ├── __init__.py
> │   │   └── routes.py
> │   ├── agents/
> │   │   ├── __init__.py
> │   │   ├── orchestrator.py
> │   │   ├── trip_structuring.py
> │   │   ├── destination.py
> │   │   ├── logistics.py
> │   │   ├── budget.py
> │   │   └── review.py
> │   ├── models/
> │   │   ├── __init__.py
> │   │   └── schemas.py
> │   ├── tools/
> │   │   ├── __init__.py
> │   │   └── router.py
> │   ├── llm/
> │   │   ├── __init__.py
> │   │   ├── groq_client.py
> │   │   └── cache.py
> │   └── utils/
> │       ├── __init__.py
> │       └── observability.py
> ├── requirements.txt
> ├── .env.example
> └── .env
> ```
>
> **Step 2 — Replicate core files from M4:**
> Read each file in `@M4/backend/app/` and create a standalone copy in `skyscanner/backend/app/`:
> - `main.py` — FastAPI app with CORS (allow `http://localhost:4200`), health endpoint
> - `config.py` — `Settings(BaseSettings)` with `groq_api_key`, `rapidapi_key: str | None = None`, `google_places_api_key: str | None = None`, `cors_origins`
> - `api/routes.py` — `POST /api/plan` (runs orchestration pipeline), `GET /health`
> - `models/schemas.py` — all Pydantic models: `PlanRequest`, `PlanResponse`, `TravelConstraints`, `FinalItinerary`, `DayItinerary`, `DayItineraryItem`, `BudgetBreakdown`, `BudgetCategory`, `ReviewStatus`, `ActivityType`
> - `agents/orchestrator.py` — Orchestrator agent (constraint extraction, worker dispatch, merge)
> - `agents/trip_structuring.py` — Trip structuring agent (regions, route type)
> - `agents/destination.py` — Destination research agent (activity catalogs)
> - `agents/logistics.py` — Logistics agent (lodging, movement, day skeletons)
> - `agents/budget.py` — Budget agent (breakdown, violations, swaps)
> - `agents/review.py` — Review agent (quality gate)
> - `tools/router.py` — `ToolRouter` with `price_band()`, `geo_estimate()`, `fx_convert()`
> - `llm/groq_client.py` — Groq LLM client with rate limiting, model fallback (gpt-oss-120b → gpt-oss-20b)
> - `llm/cache.py` — LLM response cache
> - `utils/observability.py` — Logging/tracing utilities
> - `requirements.txt` — fastapi, uvicorn, pydantic-settings, httpx, groq, python-dotenv
>
> Adapt all imports to use `app.` prefix (not M4-specific paths). Remove any M4-specific features not needed.
>
> **Step 3 — Create `.env.example`:**
> ```env
> GROQ_API_KEY=your_groq_api_key_here
> RAPIDAPI_KEY=
> GOOGLE_PLACES_API_KEY=
> CORS_ORIGINS=http://localhost:4200
> ```
>
> **Step 4 — Verify:**
> - `cd skyscanner/backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000`
> - `curl http://localhost:8000/health` returns healthy
> - `curl -X POST http://localhost:8000/api/plan -H "Content-Type: application/json" -d '{"request": "Plan a 5-day Japan trip"}'` returns a structured itinerary
> - Angular at `localhost:4200` can reach the backend via proxy
>
> **Step 5 — Create Angular frontend files:**
> - Add `provideHttpClient(withFetch())` to `@skyscanner/src/app/app.config.ts` (currently only has `provideRouter(routes)`)
> - Create `skyscanner/proxy.conf.json` with `/api` and `/health` proxying to `http://localhost:8000`
> - Register `"proxyConfig": "proxy.conf.json"` in `angular.json` serve options
> - Create `skyscanner/src/environments/environment.ts` with `apiBaseUrl: 'http://localhost:8000'`
> - Create `skyscanner/src/environments/environment.prod.ts` for production builds

---

## Prompt 5 — Implement Phase 1 (RapidAPI Flight Client)

> Implement Phase 1 from `@skyscanner/Docs/IntegrationImplementationPlan.md`.
>
> Create `skyscanner/backend/app/tools/flight_client.py` that searches for real flights via RapidAPI Skyscanner.
>
> The Angular frontend's `@skyscanner/src/app/services/skyscanner-api.service.ts` already calls the same endpoint (`skyscanner44.p.rapidapi.com/search`) — read that file to see the exact request format and how to transform the response.
>
> Implement:
> - `FlightClient` class with `search_flights(origin, destination, departure_date, return_date, cabin_class, adults)` → `list[RealFlightOffer]`
> - Single GET request to `skyscanner44.p.rapidapi.com/search` — no sessions, no polling
> - Auth: `x-rapidapi-key` + `x-rapidapi-host` headers from `Settings.rapidapi_key`
> - Response transformation: map RapidAPI response fields to `RealFlightOffer` Pydantic model
> - Hardcoded IATA code dict for demo routes (Reykjavik→KEF, Tokyo→NRT, Zurich→ZRH, Nagpur→NAG, etc.) + LLM fallback for unknown cities
> - In-memory caching by (origin+destination+dates) for 1 hour
> - Fallback: if RapidAPI unavailable, return empty list (agents fall back to LLM estimates)
> - Write tests with mocked responses
>
> Add `RealFlightOffer` model to `@skyscanner/backend/app/models/schemas.py` if not already there.

---

## Prompt 6 — Implement Phase 2 (Booking.com Hotel Client)

> Implement Phase 2 from `@skyscanner/Docs/IntegrationImplementationPlan.md`.
>
> Create `skyscanner/backend/app/tools/hotel_client.py` that searches for real hotels via Booking.com RapidAPI.
>
> Two-step pattern:
> 1. `search_destination(query)` → call `GET booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination?query=Reykjavik` → returns `dest_id` + `dest_type`
> 2. `search_hotels(dest_id, dest_type, arrival_date, departure_date, adults, room_qty)` → call `GET booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels?dest_id=...` → returns hotel results
>
> Also implement:
> - `search_hotels_by_coords(lat, lng, arrival_date, departure_date, adults)` — for when we have coordinates but no dest_id
> - Auth: same `x-rapidapi-key` as flights (RapidAPI uses one key for all subscribed APIs)
> - Transform response into `RealHotelOffer` Pydantic model: name, price/night, star rating, guest rating, reviews, photos, address, amenities, deeplink
> - Cache: 1-hour TTL for hotel results, 24-hour TTL for dest_id lookups
> - Fallback: return empty list when unavailable (agents fall back to LLM estimates)
> - Write tests with mocked responses
>
> Add `RealHotelOffer` model to `@skyscanner/backend/app/models/schemas.py` if not already there.

---

## Prompt 7 — Implement Phase 3 (Google Places Client)

> Implement Phase 3 from `@skyscanner/Docs/IntegrationImplementationPlan.md`.
>
> Create `skyscanner/backend/app/tools/google_places_client.py`:
> - `search_nearby(lat, lng, radius_meters, place_type)` — calls Google Places Nearby Search
> - `get_place_details(place_id)` — calls Google Places Details for rating, hours, photos
> - `search_text(query, location_bias)` — calls Google Places Text Search
> - Returns `PlaceInfo` objects with name, rating, review_count, opening_hours, types, coordinates, photo_url
> - Cache results for 24 hours
> - Graceful fallback: return empty list if API unavailable
>
> Add `PlaceInfo` model to `@skyscanner/backend/app/models/schemas.py` if not already there.
>
> Write tests with mocked responses.

---

## Prompt 8 — Implement Phase 4 (Extend Data Models)

> Implement Phase 4 from `@skyscanner/Docs/IntegrationImplementationPlan.md`.
>
> Extend the Pydantic models in `@skyscanner/backend/app/models/schemas.py` to carry real data:
> - Add `RealFlightOffer`, `RealHotelOffer`, `CarEstimate`, `PlaceInfo`, `MapPin`, `CostSavingTip` (if not already added in Phases 1-3)
> - Extend `DayItinerary` with `hotel_options`, `places`, `driving_time_to_next`
> - Extend `FinalItinerary` with `flight_options`, `car_estimates`, `map_pins`, `cost_saving_tips_v2`
> - Note: `CarEstimate` has `is_estimate: bool = True` since there's no real car rental API
> - Note: use `cost_saving_tips_v2` (not `cost_saving_tips`) to avoid conflict with existing `cost_optimization_tips: List[str]`
> - Make all new fields optional with defaults so existing functionality doesn't break
> - Write test fixtures with sample data

---

## Prompt 9 — Implement Phase 5 (Wire Agents for Real Data)

> Implement Phase 5 from `@skyscanner/Docs/IntegrationImplementationPlan.md`.
>
> This is the core integration phase. Wire the API clients into the agent pipeline in `skyscanner/backend/app/agents/`:
>
> Read the existing agent code at `@skyscanner/backend/app/agents/` (replicated from M4 in Phase 0).
>
> Changes:
> 1. **Orchestrator** (`orchestrator.py`) — after extracting constraints, resolve city names → IATA codes (hardcoded dict + LLM fallback) and Booking.com `dest_id` (via `HotelClient.search_destination()`). Pass resolved IDs to worker agents.
> 2. **Logistics Agent** (`logistics.py`) — call `FlightClient.search_flights()` for flights, `HotelClient.search_hotels()` for hotels at each stop, generate `CarEstimate` from `ToolRouter.price_band()` + LLM for road trips. Return real offers alongside LLM plan.
> 3. **Destination Agent** (`destination.py`) — call `GooglePlacesClient` for attractions near each stop. Merge real ratings/hours with LLM recommendations.
> 4. **Budget Agent** (`budget.py`) — use real flight + hotel prices from Logistics. Calibrated estimates for car/food/activities. Suggest cheaper hotel alternatives from same Booking.com results.
> 5. **Review Agent** (`review.py`) — validate budget against real + estimated totals.
> 6. **Orchestrator merge** — attach real data to itinerary: hotel options per day, flight options, car estimates, map pins, cost-saving tips.
>
> Important: Keep existing LLM planning logic intact. APIs INFORM and ENRICH, not replace. The LLM curates "which temples are quiet" — the APIs provide "how much does the hotel actually cost."
>
> Test with: "Plan an 11-day Iceland road trip, ₹3.5L budget"

---

## Prompt 10 — Implement Phase 6 & 7 (Angular TypeScript Models + Service)

> Implement Phase 6 and Phase 7 from `@skyscanner/Docs/IntegrationImplementationPlan.md`.
>
> 1. Read the backend models from `@skyscanner/backend/app/models/schemas.py`
> 2. Create `skyscanner/src/app/models/travel-planner.model.ts` with matching TypeScript interfaces for all response types
> 3. Create `skyscanner/src/app/services/travel-planner.service.ts` with Angular HttpClient:
>    - `generatePlan(prompt: string): Observable<PlanResponse>`
>    - `checkHealth(): Observable<any>`
>    - 90-second timeout, error handling
> 4. Add `provideHttpClient(withFetch())` to `app.config.ts` if not already there (should be done in Phase 0)

---

## Prompt 11 — Implement Phase 8 (Plan with AI Tab)

> Implement Phase 8 from `@skyscanner/Docs/IntegrationImplementationPlan.md`.
>
> Add the "Plan with AI" pill button in the navbar:
> - Position: after the Cars pill in `@skyscanner/src/app/components/navbar/navbar.component.html`
> - Label: "Plan with AI", Icon: sparkle SVG
> - Style: same as Flights/Stays/Cars pills (inactive `bg-[#072044]`, active `bg-[#0062e3]`, `rounded-full text-xs sm:text-sm font-bold`)
> - The `MainTab` type in `navbar.component.ts` already has `'ai'` — keep it as `'ai'`. Currently `setTab('ai')` calls `flightService.openAiPlanner()` and returns early — change this to emit `'ai'` as a normal tab via `tabChanged.emit('ai')`
> - **Also update `home-feed.component.ts`**: its `openTab('ai')` method calls `flightService.openAiPlanner()` directly. Change to `this.navigateTab.emit('ai')`
> - **Also update `app.ts`**: its `onTabChange('ai')` calls `flightService.openAiPlanner()` and returns early. Change to `this.currentTab.set('ai')` like other tabs
> - Update `app.html`: add `@if (currentTab() === 'ai')` section inside `<main>`, remove the modal `@if (flightService.showAiPlannerModal())` block at the bottom
> - Remove the modal overlay behavior — the AI planner should be a page, not a popup
> - Clean up `flight.service.ts`: remove `showAiPlannerModal`, `openAiPlanner()`, `closeAiPlanner()` methods

---

## Prompt 12 — Implement Phase 9 (Rewrite AI Planner Component)

> Implement Phase 9 from `@skyscanner/Docs/IntegrationImplementationPlan.md`.
>
> Rewrite `@skyscanner/src/app/components/ai-travel-planner/` to:
> - Be a full page component (remove the fixed overlay/modal wrapper)
> - Call `TravelPlannerService.generatePlan()` with the user's prompt
> - Show clean "Planning your trip..." loading state
> - On success: display the full itinerary (delegate to a child `ItineraryDisplayComponent`)
> - On error: show error message with retry button
> - Input area: large textarea with suggestion chips
> - Remove all setTimeout-based fake agent simulation code
> - Remove the hardcoded Japan-only itinerary HTML

---

## Prompt 13 — Implement Phase 10 (Gemini-style Itinerary Display)

> Implement Phase 10 from `@skyscanner/Docs/IntegrationImplementationPlan.md`.
>
> Create `skyscanner/src/app/components/itinerary-display/itinerary-display.component.ts` (and .html, .css).
>
> This component receives the `FinalItinerary` from the API and renders it like Gemini's travel planner. Sections:
>
> 1. **Trip header**: Title + summary paragraph
> 2. **Budget breakdown table**: rows per category — real prices for flights/hotels, "(estimate)" label for car/food/activities
> 3. **Day-by-day cards**: hotel options from Booking.com (name, price, rating, "Book Hotel" button), attractions with Google Places ratings, driving times
> 4. **Remaining days table**: compact Day | Region | Highlights | Overnight Base
> 5. **Google Maps embed**: route with pins from `map_pins`
> 6. **Cost-saving tips**: styled cards
> 7. **Flight summary**: cheapest options with "Search Flights" button; car estimate summary
>
> Style: Skyscanner design language — white cards, `#02122c` dark accents, `#0062e3` blue CTAs, rounded corners, Tailwind. Responsive.

---

## Prompt 14 — Implement Phase 11 & 12 (Booking + Polish)

> Implement Phase 11 and Phase 12 from `@skyscanner/Docs/IntegrationImplementationPlan.md`.
>
> 1. **Booking buttons**:
>    - "Search Flights": open deeplink from RapidAPI response, or call `FlightService.executeSearch()` with IATA codes from `airports.data.ts`
>    - "Book Hotel": open Booking.com hotel deeplink from API response
>    - Fallback: pre-fill existing app search forms
>
> 2. **Polish**:
>    - Loading skeleton while waiting for API
>    - Error states with retry button
>    - Responsive design — test on mobile viewport
>    - Cache popular routes for demo
>    - Test with: Iceland road trip, Japan city trip, Switzerland train trip, Thailand beach trip, India heritage tour

---

## Summary — Dependency Graph

```
Phase 0 (Scaffold Backend + Replicate Pipeline from M4)
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

**Phases 1, 2, 3 can run in parallel** — they are independent API clients.
**Phase 8 can run in parallel with Phases 1-5** — it's frontend-only.

---

## First Step — Getting API Keys

Before starting Phases 1-3 (not needed for Phase 0):

1. **Groq API key** — you already have this from M4. Put it in `skyscanner/backend/.env`
2. **RapidAPI key** — one key covers both Skyscanner flights and Booking.com hotels. Sign up at https://rapidapi.com, subscribe to both free tiers. Self-service, instant approval.
3. **Google Places API key** — get from https://console.cloud.google.com. Enable Places API. Free tier: ~5,000 requests/month.
