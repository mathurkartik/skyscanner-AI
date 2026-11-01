# Integration Problem Statement

## Skyscanner AI Travel Planner — Standalone

### Background

**Skyscanner app** (Angular 19, `skyscanner/`) — a full Skyscanner clone with Flights, Stays, Cars, and Explore tabs. It has live flight search via RapidAPI (`skyscanner44.p.rapidapi.com`), realistic mock data fallback with hub-and-spoke routing, 96 airports, hotel/car mock data, currency service, flight filters and sorting, favorites, and an "AI Travel Planner" modal that is currently fake — hardcoded `setTimeout` chains simulate agent steps, and the output is a static Japan itinerary.

**The goal:** Build a complete AI travel planner backend inside `skyscanner/backend/` — a standalone FastAPI server with a multi-agent LLM pipeline that produces real, bookable itineraries. The Skyscanner Angular app is the only frontend. There is no dependency on any external project at runtime.

**Reference code:** The `M4/backend/` project contains a working multi-agent AI pipeline (Orchestrator → Trip Structuring → parallel(Destination Research, Logistics, Budget) → Review → Repair) powered by Groq LLMs. This code serves as a **template to replicate from** — the pipeline structure, agent prompts, Pydantic models, LLM client, and tool router can be copied and adapted into `skyscanner/backend/`. At runtime, `skyscanner/backend/` runs independently with zero imports from M4.

---

### The Problem

The Skyscanner app's AI planner is a hardcoded animation with no real intelligence. To make it real, it needs:

1. A **backend AI pipeline** that plans trips using LLMs (replicated from M4's working pipeline)
2. **Real flight data** from RapidAPI Skyscanner — not LLM-hallucinated prices
3. **Real hotel data** from Booking.com RapidAPI — not made-up hotel names
4. **Real attraction data** from Google Places API — not generic descriptions
5. **Calibrated car rental estimates** — no free car API exists, but LLM estimates can be grounded in regional price bands

**The user's need: "Plan my trip with real prices I can actually book."**

---

### Objective

Build a standalone backend at `skyscanner/backend/` so that:

1. `POST /api/plan` runs a multi-agent LLM pipeline (replicated from M4) that produces day-by-day itineraries
2. The pipeline uses **real API data** for flights (RapidAPI Skyscanner) and hotels (Booking.com RapidAPI)
3. The pipeline uses **Google Places API data** for attractions — real ratings, opening hours, and photos
4. The pipeline uses **LLM estimates calibrated by regional price bands** for car rentals
5. The Skyscanner Angular app displays the AI-generated itinerary with real data in a Gemini-style format
6. Users can click through from the itinerary to **actual booking pages** for flights and hotels

---

### What "Done" Looks Like

A user types a natural-language request like:

> "Plan an 11-day Iceland road trip, ₹3.5L budget"

And gets back:

| Section | Content | Data Source |
|---------|---------|-------------|
| Budget breakdown table | Flights ₹75-85K, Car ₹55-65K, Hotels ₹80-95K, Food ₹30-35K, Activities ₹25-30K | Calculated from real flight + hotel prices, LLM estimates for car/food/activities |
| Day 1: Reykjavik | SM Hostel ₹9,371/night or B18 Apartments ₹16,669/night | Booking.com RapidAPI |
| Day 2: Golden Circle | Thingvellir National Park (4.7★), Geysir, Gullfoss, Secret Lagoon ₹4,000/person | Google Places API |
| Day 3: South Coast → Vik | Guesthouse Carina ₹12,033/night, Seljalandsfoss, Skógafoss, Reynisfjara Beach | Booking.com RapidAPI + Google Places |
| Flight options | IndiGo via Mumbai, ₹75,000 round-trip | RapidAPI Skyscanner |
| Car rental | Hertz compact AWD, ~₹55,000 for 11 days | LLM estimate (calibrated by region) |
| Route map | Pins at each overnight stop on Google Maps | Google Maps Embed API |
| Cost-saving tips | "Cook at Bónus/Krónan", "Never decline gravel protection" | LLM knowledge |
| Booking buttons | "Search Flights" → RapidAPI deeplinks, "Book Hotel" → Booking.com links | API response links |

---

### What Exists Today (Exact Current State)

#### Skyscanner App — Key Files

| File | What It Does | What Changes |
|------|-------------|--------------|
| `src/app/components/navbar/navbar.component.ts` | Defines `MainTab = 'flights' \| 'hotels' \| 'cars' \| 'explore' \| 'ai'`. When `'ai'` is selected, calls `flightService.openAiPlanner()` and returns early (opens a modal, doesn't switch tab). | Make `'ai'` work like other tabs — switch to a full page view |
| `src/app/components/navbar/navbar.component.html` | Has pill buttons for Flights, Stays, Cars. No "Plan with AI" pill. | Add "Plan with AI" pill after Cars |
| `src/app/app.html` | Switches between `<app-flight-search>`, `<app-hotel-search>`, `<app-car-search>`, `<app-explore-everywhere>` based on `currentTab()`. AI planner is a separate modal overlay: `@if (flightService.showAiPlannerModal()) { <app-ai-travel-planner> }` | Add `@if (currentTab() === 'ai')` section, remove modal overlay |
| `src/app/app.ts` | `onTabChange()` handles `'ai'` by calling `flightService.openAiPlanner()` instead of setting `currentTab` | Let `'ai'` set `currentTab` like other tabs |
| `src/app/components/ai-travel-planner/ai-travel-planner.component.ts` | Fake planner: 5 hardcoded `AgentStep` objects, `setTimeout` chains at 400/1200/2400/3200ms, `loadPlanIntoSkyscanner()` hardcoded to Tokyo HND | Rewrite entirely — call real backend, display real itinerary |
| `src/app/components/home-feed/home-feed.component.ts` | Has a "Search with AI" card tile on the flights landing page. `openTab('ai')` calls `flightService.openAiPlanner()` directly — same modal behavior as navbar. | Change to emit `'ai'` via `navigateTab` so `app.ts` switches to the AI tab page |
| `src/app/services/flight.service.ts` | Has `showAiPlannerModal` signal, `openAiPlanner()`, `closeAiPlanner()` methods for modal behavior | Remove modal methods once AI planner is a tab page |
| `src/app/services/skyscanner-api.service.ts` | Wraps RapidAPI `skyscanner44.p.rapidapi.com` for live flight search | Keep as fallback; primary source becomes the backend |
| `src/app/app.config.ts` | Has `provideRouter(routes)` only — no `provideHttpClient()` | Add `provideHttpClient(withFetch())` for API calls to backend |
| `src/app/app.routes.ts` | Empty: `routes: Routes = []` | May stay empty (tab-based navigation) or add route for AI planner |
| `src/app/models/flight.model.ts` | `FlightOffer`, `Airport`, `SearchQuery`, etc. | Keep; add new interfaces for AI planner response |
| `src/app/models/travel.model.ts` | `HotelOffer`, `CarOffer`, `ExploreDestination` | Keep; extend for real API offers |
| `src/app/data/airports.data.ts` | 96 airports (India, Iceland, Europe, Asia, Americas, etc.) | May need more airports for new destinations |
| `src/app/data/travel.data.ts` | Mock hotels (Park Hyatt Tokyo, etc.), cars (Hertz, Avis), explore destinations | Keep as fallback data |

#### New Backend to Create — `skyscanner/backend/`

This is a new standalone FastAPI backend. Its structure is replicated from `M4/backend/` but runs independently.

| File to Create | What It Does | Reference in M4 |
|----------------|-------------|-----------------|
| `backend/app/main.py` | FastAPI app with CORS middleware, health check | `M4/backend/app/main.py` |
| `backend/app/config.py` | `Settings(BaseSettings)` with `groq_api_key`, `rapidapi_key`, `google_places_api_key`, `cors_origins` | `M4/backend/app/config.py` |
| `backend/app/api/routes.py` | `POST /api/plan` — runs orchestration pipeline. `GET /health` | `M4/backend/app/api/routes.py` |
| `backend/app/models/schemas.py` | Pydantic models: `PlanRequest`, `PlanResponse`, `TravelConstraints`, `FinalItinerary`, `DayItinerary`, `BudgetBreakdown`, plus new `RealFlightOffer`, `RealHotelOffer`, `PlaceInfo`, `CarEstimate`, `MapPin` | `M4/backend/app/models/schemas.py` |
| `backend/app/agents/orchestrator.py` | Extracts constraints, dispatches to workers, merges results, resolves IATA codes + Booking.com dest_ids | `M4/backend/app/agents/orchestrator.py` |
| `backend/app/agents/destination.py` | LLM-powered activity catalog + Google Places API for real ratings | `M4/backend/app/agents/destination.py` |
| `backend/app/agents/logistics.py` | Lodging plans + RapidAPI flights + Booking.com hotels + car estimates | `M4/backend/app/agents/logistics.py` |
| `backend/app/agents/budget.py` | Budget breakdown using real flight + hotel prices | `M4/backend/app/agents/budget.py` |
| `backend/app/agents/review.py` | Quality gate: validates against real price totals | `M4/backend/app/agents/review.py` |
| `backend/app/agents/trip_structuring.py` | Determines trip type and geographic regions | `M4/backend/app/agents/trip_structuring.py` |
| `backend/app/tools/router.py` | `ToolRouter` with price_band, geo_estimate, fx_convert | `M4/backend/app/tools/router.py` |
| `backend/app/tools/flight_client.py` | RapidAPI Skyscanner flight search (NEW — not in M4) | — |
| `backend/app/tools/hotel_client.py` | Booking.com RapidAPI hotel search (NEW — not in M4) | — |
| `backend/app/tools/google_places_client.py` | Google Places API client (NEW — not in M4) | — |
| `backend/app/llm/groq_client.py` | Groq LLM client with rate limiting and fallback models | `M4/backend/app/llm/groq_client.py` |
| `backend/app/llm/cache.py` | LLM response cache | `M4/backend/app/llm/cache.py` |
| `backend/requirements.txt` | Python dependencies | `M4/backend/requirements.txt` |
| `backend/.env.example` | Environment variable template | `M4/backend/.env.example` |

---

### Data Sources

| Data | Primary Source | Fallback |
|------|---------------|----------|
| Flights | RapidAPI Skyscanner — `GET skyscanner44.p.rapidapi.com/search` (server-side client in `skyscanner/backend/`) | LLM estimates + `ToolRouter.price_band()` |
| Hotels | Booking.com RapidAPI — `GET booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels` (server-side client in `skyscanner/backend/`) | Mock data from `travel.data.ts` + LLM-generated names |
| City → Hotel dest_id | Booking.com RapidAPI — `GET booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination` | Hardcoded mapping for popular destinations |
| Car rentals | LLM estimates calibrated by `ToolRouter.price_band()` + curated regional data | Same (no free car rental API exists) |
| Attractions | Google Places API (Nearby Search + Place Details) | LLM-generated data |
| Route maps | Google Maps Embed API | No map shown |
| Trip planning logic | Multi-agent pipeline in `skyscanner/backend/` (Groq LLM) | Stub itinerary |

Both RapidAPI services use simple **GET requests** with `x-rapidapi-key` and `x-rapidapi-host` headers. No session tokens, no polling — single request/response.

All API keys live in `skyscanner/backend/` only. The Angular frontend has zero API keys.

---

### User Experience

1. User clicks **"Plan with AI"** pill in the navbar (new, after Cars pill, with sparkle icon)
2. Full page opens (same pattern as Flights/Stays/Cars tabs — not a modal)
3. User types their request in a textarea, or clicks a suggestion chip
4. "Planning your trip..." loading state (30-60 seconds while backend queries APIs)
5. Complete itinerary appears: budget table → day-by-day cards → map → tips → booking buttons
6. "Search Flights" / "Book Hotel" buttons link to real booking pages
7. No login required — open to everyone

---

### Constraints

- **RapidAPI free tier** is limited (~100-500 requests/month per API). Cache aggressively and pre-warm demo routes.
- **Google Places API** has a free tier (~5,000 requests/month for Nearby Search and Text Search). Cache aggressively (place data changes slowly).
- **Groq free tier** has rate limits (8k TPM for gpt-oss-120b). The pipeline handles this with fallback to gpt-oss-20b.
- **No free car rental API** exists — car costs use LLM estimates calibrated by regional price bands. This is acceptable for a demo.
- **Response time** will be 30-60 seconds (LLM pipeline + multiple API calls). A simple loading state is sufficient — no streaming/live agent updates.
- **Demo context**: This is a portfolio project for a Skyscanner PM interview. It needs to work reliably as a live demo.

---

### Success Criteria

1. `POST /api/plan` (served by `skyscanner/backend/`) with "11-day Iceland road trip, ₹3.5L budget" returns real hotel names/prices (from Booking.com), real flight prices (from RapidAPI Skyscanner), and real attraction ratings (from Google Places)
2. Budget breakdown uses actual API prices for flights and hotels, calibrated LLM estimates for car/food/activities
3. "Plan with AI" tab works in the Skyscanner app as a full page (not modal)
4. Booking buttons open real booking/search pages for flights and hotels
5. Fallback works: if any API is unavailable, the planner still produces a useful itinerary using LLM data
6. End-to-end demo takes under 90 seconds from prompt to result
7. `skyscanner/backend/` runs independently — zero imports from or runtime dependency on M4
