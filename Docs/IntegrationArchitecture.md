# Integration Architecture

## Skyscanner AI Travel Planner — Standalone

Reference: `IntegrationProblemStatement.md`

**Reference code:** `M4/backend/` contains a working multi-agent pipeline. Its code is replicated into `skyscanner/backend/` as a standalone copy. At runtime, `skyscanner/backend/` has zero dependency on M4.

---

## 1. System Overview

```
┌─────────────────────────────────┐
│  Skyscanner Angular App         │
│  (localhost:4200)               │
│                                 │
│  "Plan with AI" tab             │
│  → POST /api/plan               │
│  ← FinalItinerary + real data   │
│  → Renders Gemini-style output  │
│  → "Book" buttons → deeplinks   │
└──────────┬──────────────────────┘
           │ HTTP (proxy or CORS)
           ▼
┌─────────────────────────────────────────────────────────┐
│  Skyscanner Backend (skyscanner/backend/)                │
│  FastAPI (localhost:8000)                                │
│                                                         │
│  POST /api/plan                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Orchestrator Agent                               │    │
│  │  1. Extract constraints (Groq LLM)               │    │
│  │  2. Resolve city → IATA codes + Booking dest_id  │    │
│  │  3. Trip Structuring (regions, route)             │    │
│  │  4. Parallel per region:                          │    │
│  │     ┌──────────────┬──────────────┬────────────┐ │    │
│  │     │ Destination  │ Logistics    │ Budget     │ │    │
│  │     │ Agent        │ Agent        │ Agent      │ │    │
│  │     │              │              │            │ │    │
│  │     │ Google       │ RapidAPI     │ Uses real  │ │    │
│  │     │ Places API   │ Skyscanner   │ prices     │ │    │
│  │     │              │ (flights)    │ from       │ │    │
│  │     │              │ Booking.com  │ Logistics  │ │    │
│  │     │              │ RapidAPI     │            │ │    │
│  │     │              │ (hotels)     │            │ │    │
│  │     └──────────────┴──────────────┴────────────┘ │    │
│  │  5. Merge → DraftItinerary with real data         │    │
│  │  6. Review Agent (validate real totals)            │    │
│  │  7. Return FinalItinerary                         │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  External API calls (all from backend, never frontend): │
│  • RapidAPI Skyscanner (skyscanner44.p.rapidapi.com)    │
│  • Booking.com RapidAPI (booking-com15.p.rapidapi.com)  │
│  • Google Places API (maps.googleapis.com)              │
│  • Groq LLM API (api.groq.com)                         │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Data Source Layer — RapidAPI Flight Client

### 2.1 New Module: `skyscanner/backend/app/tools/flight_client.py`

Host: `skyscanner44.p.rapidapi.com`
Auth: `x-rapidapi-key` + `x-rapidapi-host` headers from `Settings.rapidapi_key`

This is the same RapidAPI endpoint the Angular frontend's `skyscanner-api.service.ts` already uses, reimplemented server-side so no API keys are in the frontend.

**Method:**

```python
async def search_flights(
    origin_code: str,       # "NAG" (IATA)
    destination_code: str,  # "KEF" (IATA)
    departure_date: str,    # "2026-12-01"
    return_date: str | None,
    cabin_class: str,       # "economy"
    adults: int
) -> list[RealFlightOffer]:
    # Single GET request — no session tokens, no polling
    url = "https://skyscanner44.p.rapidapi.com/search"
    params = {
        "adults": adults,
        "origin": origin_code,
        "destination": destination_code,
        "departureDate": departure_date,
        "cabinClass": cabin_class,
        "currency": "USD"
    }
    if return_date:
        params["returnDate"] = return_date
    # ... fetch, transform, return
```

**Response data:** airline name, price, duration, stops, departure/arrival times, carrier logos. The Angular frontend's `transformSkyscannerResponse()` in `skyscanner-api.service.ts` already maps this format — reuse the same field paths.

**Caching:** In-memory dict keyed by `(origin + destination + dates)`, TTL 1 hour. Same pattern as `ToolRouter._cache` (replicated from M4).

**Fallback:** If RapidAPI is unavailable, fall back to `ToolRouter.price_band()` for flight estimates + LLM-generated data.

### 2.2 City Name → IATA Code Resolution

The RapidAPI Skyscanner flight search needs IATA airport codes (e.g., "KEF" for Reykjavik), not city names. Resolution options:

1. **`airports.data.ts`** — the Skyscanner app already has 96 airports with IATA codes. Export this as a JSON lookup table for the backend.
2. **LLM-based** — the Orchestrator agent can ask the LLM to resolve city names to IATA codes (reliable for major cities).
3. **Hardcoded mapping** — for demo routes (Iceland→KEF, Japan→NRT/HND, Switzerland→ZRH), a static dict is sufficient.

Recommended: Start with option 3 (hardcoded) + option 2 (LLM fallback). Expand to option 1 if needed.

---

## 3. Data Source Layer — Booking.com Hotel Client

### 3.1 New Module: `skyscanner/backend/app/tools/hotel_client.py`

Host: `booking-com15.p.rapidapi.com`
Auth: `x-rapidapi-key` + `x-rapidapi-host` headers from `Settings.rapidapi_key` (same key as flights — RapidAPI uses one key for all subscribed APIs)

**Two-step pattern: resolve destination, then search hotels.**

**Step 1 — Resolve city name to `dest_id`:**

```python
async def search_destination(query: str) -> dict:
    # GET /api/v1/hotels/searchDestination?query=Reykjavik
    # Returns: [{ dest_id: "900040261", dest_type: "city", label: "Reykjavik, Iceland", ... }]
```

**Step 2 — Search hotels:**

```python
async def search_hotels(
    dest_id: str,           # "900040261"
    dest_type: str,         # "city"
    arrival_date: str,      # "2026-12-01"
    departure_date: str,    # "2026-12-02"
    adults: int,
    room_qty: int
) -> list[RealHotelOffer]:
    # GET /api/v1/hotels/searchHotels?dest_id=...&arrival_date=...
    # Returns: hotel name, price, star rating, guest rating, review count, photos, address, amenities
```

**Alternative — search by coordinates:**

```python
async def search_hotels_by_coords(
    latitude: float,        # 64.1466
    longitude: float,       # -21.9426
    arrival_date: str,
    departure_date: str,
    adults: int
) -> list[RealHotelOffer]:
    # GET /api/v1/hotels/searchHotelsByCoordinates?latitude=...&longitude=...
    # Useful when we have coordinates from Google Places but no dest_id
```

**Response data:** hotel name, price per night, star rating, guest review score, review count, photos, address/neighborhood, amenities, hotel_id. Booking deeplinks for each hotel.

**Caching:** In-memory dict keyed by `(dest_id + dates)`, TTL 1 hour. Also cache `dest_id` lookups separately with 24-hour TTL (city→dest_id mappings are stable).

**Fallback:** If Booking.com RapidAPI is unavailable, fall back to mock hotel data from `travel.data.ts` + LLM-generated names and estimates.

**Free tier note:** The Booking.com RapidAPI free tier is limited (~100-500 requests/month). Cache aggressively and pre-warm demo routes. For the interview demo, you only need 3-5 real hotel searches.

---

## 4. Data Source Layer — Google Places API

### New Module: `skyscanner/backend/app/tools/google_places_client.py`

Auth: `Settings.google_places_api_key`

**Methods:**

| Method | Google API | Returns |
|--------|-----------|---------|
| `search_nearby(lat, lng, radius_m, type)` | Places Nearby Search | List of places with name, place_id, rating, location |
| `get_place_details(place_id)` | Place Details | Full details: name, rating, review_count, opening_hours, types, photos, formatted_address |
| `search_text(query, location_bias)` | Text Search | Places matching a query near a location |

**Caching:** 24-hour TTL (place data is stable). Keyed by `(place_id)` for details, `(lat, lng, radius, type)` for nearby.

**Fallback:** Return empty list if API unavailable or key not set. The LLM still generates attraction recommendations — Google Places enriches them with real ratings and hours.

---

## 5. Data Source Layer — Car Rentals (No API)

No free, self-service car rental API exists. Car rental data uses:

1. **`ToolRouter.price_band()`** — regional pricing stubs (Japan, Scandinavia, Western Europe, SE Asia, etc.)
2. **Curated regional data** — realistic supplier names (Hertz, Avis, Sixt, Europcar), vehicle categories, and daily rates per region, stored in a config dict
3. **LLM estimates** — the LLM generates car rental recommendations using its knowledge, calibrated by the price band data

This is acceptable for a demo — the interviewer won't verify live car rental prices. The itinerary shows realistic supplier names and price ranges.

---

## 6. Extended Data Models

### Pydantic models in `skyscanner/backend/app/models/schemas.py`:

These models are replicated from M4's `schemas.py` and extended with real data fields.

```python
class RealFlightOffer(BaseModel):
    airline: str                    # "IndiGo"
    flight_number: Optional[str]    # "6E 1234"
    price: float                    # 75000
    currency: str                   # "INR"
    duration_minutes: int           # 840
    stops: int                      # 1
    stop_cities: list[str]          # ["Mumbai"]
    departure: str                  # "2026-11-15T06:30"
    arrival: str                    # "2026-11-15T22:30"
    deeplink: Optional[str]         # Booking URL

class RealHotelOffer(BaseModel):
    name: str                       # "SM Hostel"
    price_per_night: float          # 9371
    currency: str                   # "INR"
    star_rating: Optional[float]    # 3.0
    guest_rating: Optional[float]   # 8.2
    review_count: Optional[int]     # 450
    neighborhood: Optional[str]     # "Laugavegur, Reykjavik"
    image_url: Optional[str]
    deeplink: Optional[str]         # Booking.com hotel URL
    amenities: list[str]            # ["WiFi", "Breakfast"]

class CarEstimate(BaseModel):
    supplier: str                   # "Hertz"
    vehicle_name: str               # "Toyota Yaris or similar"
    category: str                   # "Compact AWD"
    price_per_day: float            # 5000
    total_price: float              # 55000
    currency: str                   # "INR"
    seats: int                      # 5
    transmission: str               # "Automatic"
    is_estimate: bool = True        # Always true — no real API

class PlaceInfo(BaseModel):
    name: str                       # "Thingvellir National Park"
    rating: Optional[float]         # 4.7
    review_count: Optional[int]     # 12500
    types: list[str]                # ["national_park", "tourist_attraction"]
    opening_hours: Optional[str]    # "Open 24 hours" or "09:00-17:00"
    coordinates: Optional[tuple[float, float]]  # (64.2559, -21.1290)
    photo_url: Optional[str]
    description: Optional[str]      # From LLM, not Places API

class MapPin(BaseModel):
    label: str                      # "Day 1: Reykjavik"
    lat: float
    lng: float
    day_number: int
    pin_type: str                   # "overnight" | "attraction" | "transit"

class CostSavingTip(BaseModel):
    title: str                      # "Cook at Bónus/Krónan"
    description: str                # "Iceland's discount groceries..."
```

### Extensions to existing models (replicated from M4, then extended):

```python
# DayItinerary — add optional fields (backward compatible)
class DayItinerary(BaseModel):
    # ... existing fields replicated from M4 ...
    hotel_options: list[RealHotelOffer] = []      # NEW: 1-3 real hotel options for this stop
    places: list[PlaceInfo] = []                   # NEW: real attraction data for this day
    driving_time_to_next: Optional[str] = None     # NEW: "2h 30min to Vik"

# FinalItinerary — add optional fields (backward compatible)
class FinalItinerary(BaseModel):
    # ... existing fields replicated from M4 ...
    flight_options: list[RealFlightOffer] = []     # NEW: real flight offers
    car_estimates: list[CarEstimate] = []           # NEW: LLM-calibrated car estimates
    map_pins: list[MapPin] = []                    # NEW: coordinates for map
    cost_saving_tips_v2: list[CostSavingTip] = []  # NEW: structured tips (named _v2 to avoid conflict with existing cost_optimization_tips)
```

All new fields have defaults (`= []` or `= None`) so the API works even before real data sources are wired in.

---

## 7. Agent Pipeline (Replicated from M4)

The agent pipeline is copied from `M4/backend/app/agents/` and adapted to use real API data. The agents keep the same roles and LLM prompts. The change is **where they get data from**: real APIs for flights and hotels, calibrated estimates for cars, and Google Places for attractions.

### 7.1 Orchestrator Agent (`orchestrator.py`)

**New step after constraint extraction:**

```
Extract constraints (replicated from M4)
    ↓
Resolve city names → IATA codes for flights (hardcoded map + LLM fallback)
Resolve city names → Booking.com dest_id via searchDestination API (NEW)
    ↓
Trip Structuring (replicated from M4)
    ↓
Dispatch to workers with resolved IDs (enhanced)
```

**New step during merge:**

After merging worker outputs into `DraftItinerary`, the Orchestrator:
1. Attaches `hotel_options` to each `DayItinerary` from Logistics results
2. Attaches `places` to each `DayItinerary` from Destination results
3. Generates `map_pins` from the coordinates of each overnight stop
4. Generates `cost_saving_tips_v2` via LLM based on destination knowledge
5. Attaches `flight_options` and `car_estimates` to `FinalItinerary`

### 7.2 Destination Research Agent (`destination.py`)

**What changes:**
- After LLM generates activity recommendations, call `GooglePlacesClient.search_text()` for each recommended place
- Merge real data: replace LLM-estimated ratings with Google Places ratings, add opening hours, add photo URLs
- LLM still curates which places to recommend, crowd avoidance, and "must-do vs nice-to-have" — Google Places provides the facts

**What stays the same:**
- `ActivityCatalog` structure (replicated from M4)
- LLM-based curation logic
- Neighborhood notes

### 7.3 Logistics Agent (`logistics.py`)

**What changes:**
- After LLM generates lodging plans and movement plans:
  - Call `FlightClient.search_flights()` for inter-city flights (origin → destination, and return)
  - Call `HotelClient.search_hotels()` for each overnight stop (using resolved dest_id, or coordinates)
  - Generate `CarEstimate` using `ToolRouter.price_band()` + LLM knowledge if road trip
- Return real offers alongside LLM-generated plans
- Include deeplinks from API responses

**What stays the same:**
- `LodgingPlan`, `MovementPlan`, `DaySkeleton` structures (replicated from M4)
- LLM-based route optimization and day sequencing
- Backtracking minimization logic

### 7.4 Budget Agent (`budget.py`)

**What changes:**
- Receive real flight prices and hotel prices from Logistics agent output
- Calculate actual category totals: real hotel prices × nights, real flight prices
- Car estimate from `ToolRouter.price_band()` (calibrated, not hallucinated)
- Food estimate stays LLM-based with `ToolRouter.price_band()` calibration
- Activity costs stay LLM-based with Google Places data for paid attractions
- `within_budget` check uses real+estimated totals
- `suggested_swaps` uses cheaper hotel alternatives from the same Booking.com search results

**What stays the same:**
- `BudgetBreakdown` structure (replicated from M4, with `grand_total` now more accurate)
- Violation detection
- LLM-generated budget strategy narrative

### 7.5 Review Agent (`review.py`)

**What changes:**
- Budget validation uses real flight + hotel totals, calibrated car/food/activity estimates
- Can flag "no hotel results found for Day 4" as a warning if API returned empty

**What stays the same:**
- All existing checklist items (duration match, cities included, preferences satisfied, crowd avoidance)
- Pass/warnings/fail status
- Repair hints

---

## 8. Angular Frontend Changes

### 8.1 Navbar: "Plan with AI" Pill

Add after the Cars pill in `navbar.component.html`:

```html
<!-- Plan with AI Pill -->
<button 
  (click)="setTab('ai')"
  [class.bg-[#0062e3]]="activeTab() === 'ai'"
  [class.text-white]="activeTab() === 'ai'"
  [class.bg-[#072044]]="activeTab() !== 'ai'"
  [class.text-gray-200]="activeTab() !== 'ai'"
  class="flex items-center space-x-2 px-4 py-2 rounded-full text-xs sm:text-sm font-bold ...">
  <svg><!-- sparkle icon --></svg>
  <span>Plan with AI</span>
</button>
```

**Behavior change in `navbar.component.ts`:** Currently `setTab('ai')` calls `flightService.openAiPlanner()` and returns early. Change to emit `'ai'` as a normal tab via `tabChanged.emit('ai')` so `app.ts` switches the page view.

### 8.2 App Template + Home Feed: AI Planner as Page

**Two places currently open the modal — both need updating:**

1. `app.ts` `onTabChange('ai')` — currently calls `flightService.openAiPlanner()` and returns early. Change to `this.currentTab.set('ai')` like other tabs.
2. `home-feed.component.ts` `openTab('ai')` — same modal shortcut. Change to `this.navigateTab.emit('ai')` so it flows through `app.ts`.

In `app.html`, add alongside the other tab sections:

```html
@if (currentTab() === 'ai') {
  <app-ai-travel-planner></app-ai-travel-planner>
}
```

Remove the modal overlay block at the bottom:
```html
<!-- REMOVE THIS -->
@if (flightService.showAiPlannerModal()) {
  <app-ai-travel-planner></app-ai-travel-planner>
}
```

### 8.3 New Service: `travel-planner.service.ts`

```typescript
@Injectable({ providedIn: 'root' })
export class TravelPlannerService {
  private http = inject(HttpClient);
  
  generatePlan(prompt: string): Observable<PlanResponse> {
    return this.http.post<PlanResponse>('/api/plan', { request: prompt })
      .pipe(timeout(90000));  // 90s timeout for real API calls
  }
}
```

### 8.4 New TypeScript Interfaces: `travel-planner.model.ts`

Matching all Pydantic models from `skyscanner/backend/app/models/schemas.py`: `PlanResponse`, `FinalItinerary`, `DayItinerary`, `RealFlightOffer`, `RealHotelOffer`, `CarEstimate`, `PlaceInfo`, `MapPin`, `CostSavingTip`, `BudgetBreakdown`.

### 8.5 Rewritten AI Planner Component

Replace `ai-travel-planner.component.ts` entirely:
- Full page layout (not modal overlay)
- Textarea input with suggestion chips
- "Planning your trip..." loading state
- Itinerary display component (child) for the Gemini-style output
- Error state with retry button

### 8.6 New Itinerary Display Component

`itinerary-display.component.ts` — renders the `FinalItinerary`:
1. Trip header + summary
2. Budget breakdown table (rows per category — real prices for flights/hotels, estimates for car/food/activities)
3. Day-by-day cards (hotel options, attractions with ratings, driving times)
4. Google Maps embed with route pins
5. Cost-saving tips
6. Flight summary with booking buttons, car estimate summary
7. Responsive, matches Skyscanner's design language

---

## 9. Communication Flow

```
User types: "Plan an 11-day Iceland road trip, ₹3.5L budget"
    │
    ▼
Angular: POST /api/plan { request: "..." }
    │
    ▼
Skyscanner Backend Orchestrator:
    ├── Extract constraints → { destination: "Iceland", duration: 11, budget: 350000, currency: "INR", is_road_trip: true }
    ├── Resolve "Reykjavik" → IATA "KEF" (hardcoded map), Booking.com dest_id (searchDestination API)
    ├── Resolve "Nagpur" → IATA "NAG" (hardcoded map)
    ├── Trip Structuring → { regions: ["Reykjavik", "Golden Circle", "South Coast", "East Fjords", "North Iceland", "Snæfellsnes"] }
    │
    ├── Per region, parallel:
    │   ├── Destination Agent → Google Places → real attraction names, ratings, hours
    │   ├── Logistics Agent → RapidAPI Skyscanner (flights) + Booking.com RapidAPI (hotels) + car estimate
    │   └── Budget Agent → real flight/hotel prices + calibrated car/food estimates → actual totals
    │
    ├── Merge → DraftItinerary with real hotel_options, places, flight_options, car_estimates, map_pins
    ├── Review → validate real+estimated totals against budget
    │
    └── Return FinalItinerary
    │
    ▼
Angular: Render Gemini-style itinerary
    ├── Budget table (real flight/hotel prices, calibrated estimates for rest)
    ├── Day cards (real hotel names + prices, real attraction ratings)
    ├── Google Maps embed (real coordinates)
    ├── Cost-saving tips
    └── "Search Flights" → RapidAPI deeplinks, "Book Hotel" → Booking.com links
```

---

## 10. Environment and Configuration

### Skyscanner Backend (`skyscanner/backend/app/config.py`)

```python
class Settings(BaseSettings):
    # App
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:4200"
    
    # LLM
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_fallback_model: str | None = "openai/gpt-oss-20b"
    
    # External APIs
    rapidapi_key: str | None = None          # Shared for Skyscanner flights + Booking.com hotels
    google_places_api_key: str | None = None
    
    # Token Budget Management (Groq = 100k tokens/day)
    enable_token_tracking: bool = True
    max_tokens_per_plan_request: int = 15000
```

### Angular (`skyscanner/`)

`src/environments/environment.ts`:
```typescript
export const environment = {
  production: false,
  apiBaseUrl: 'http://localhost:8000'
};
```

`proxy.conf.json`:
```json
{
  "/api": {
    "target": "http://localhost:8000",
    "secure": false
  }
}
```

---

## 11. Fallback Strategy

Every external API has a fallback so the demo always works:

| API | Fallback When Unavailable | Behavior |
|-----|---------------------------|----------|
| RapidAPI Skyscanner (flights) | LLM estimates + `ToolRouter.price_band()` | Plausible but not real prices, no deeplinks |
| Booking.com RapidAPI (hotels) | Mock data from `travel.data.ts` + LLM-generated names | Plausible hotel names, estimated prices |
| Google Places | Empty list — LLM still generates attraction recommendations | No real ratings/hours, but itinerary still works |
| Groq LLM | Stub itinerary (implemented in `routes.py`) | Generic but structured output |
| Car rentals | Already LLM-estimated — no degradation | Same output regardless |

**Caching for demo reliability:**
- RapidAPI responses (flights + hotels): 1-hour TTL
- Booking.com `dest_id` lookups: 24-hour TTL
- Google Places responses: 24-hour TTL
- Popular routes can be pre-warmed by calling the API once before the demo

---

## 12. What Stays Unchanged

These parts of the Skyscanner project need zero modifications:

**Skyscanner App:**
- `flight-search`, `flight-results`, `flight-card`, `flight-filters`, `flight-details-modal` — entire flights flow unchanged
- `hotel-search`, `car-search`, `explore-everywhere` — other tabs unchanged
- `currency.service.ts`, `favorites.service.ts` — utility services unchanged
- `airports.data.ts`, `flights.data.ts`, `travel.data.ts`, `faq.data.ts` — static data unchanged
- `footer.component.ts`, `api-settings-modal.component.ts` — UI components unchanged

## 13. What Gets Replicated from M4

These M4 files are **copied and adapted** into `skyscanner/backend/`. The copies are then modified to add real API data:

| M4 Source | Skyscanner Target | Adaptation |
|-----------|-------------------|------------|
| `M4/backend/app/agents/orchestrator.py` | `skyscanner/backend/app/agents/orchestrator.py` | Add IATA + dest_id resolution, real data merge |
| `M4/backend/app/agents/destination.py` | `skyscanner/backend/app/agents/destination.py` | Add Google Places API calls |
| `M4/backend/app/agents/logistics.py` | `skyscanner/backend/app/agents/logistics.py` | Add flight + hotel API calls |
| `M4/backend/app/agents/budget.py` | `skyscanner/backend/app/agents/budget.py` | Use real prices from APIs |
| `M4/backend/app/agents/review.py` | `skyscanner/backend/app/agents/review.py` | Validate real totals |
| `M4/backend/app/agents/trip_structuring.py` | `skyscanner/backend/app/agents/trip_structuring.py` | No changes needed |
| `M4/backend/app/models/schemas.py` | `skyscanner/backend/app/models/schemas.py` | Add new real data models |
| `M4/backend/app/tools/router.py` | `skyscanner/backend/app/tools/router.py` | Keep as-is for price bands |
| `M4/backend/app/llm/groq_client.py` | `skyscanner/backend/app/llm/groq_client.py` | No changes needed |
| `M4/backend/app/llm/cache.py` | `skyscanner/backend/app/llm/cache.py` | No changes needed |
| `M4/backend/app/main.py` | `skyscanner/backend/app/main.py` | Simplify CORS to just localhost:4200 |
| `M4/backend/app/api/routes.py` | `skyscanner/backend/app/api/routes.py` | Keep /api/plan + /health |
| `M4/backend/app/config.py` | `skyscanner/backend/app/config.py` | Add rapidapi_key, google_places_api_key |
| `M4/backend/requirements.txt` | `skyscanner/backend/requirements.txt` | Add httpx for API calls |
