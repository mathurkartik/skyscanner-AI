# Stitch Prompt — AI Travel Planner Tab (Full-Page View)

## Context for Stitch

Design a full-page "Plan with AI" tab inside a Skyscanner clone. This is NOT a modal — it replaces the main content area when the user clicks the "Plan with AI" pill in the top nav (alongside Flights, Stays, Cars). The page uses Skyscanner's exact design language: `#02122c` dark navy header, `#0062e3` CTA blue, `#f1f3f8` light gray canvas, white rounded cards with subtle borders, and Inter/system font stack.

---

## Page Structure (Top to Bottom)

### 1. Hero Input Card (always visible)

Dark navy (`#02122c`) card with rounded corners, sitting on the light gray canvas.

Contents:
- **Sparkle icon + "Plan with AI" heading** with a small pill badge saying "Multi-Agent System"
- **Subtitle**: "Live Skyscanner Flights · Booking.com Hotels · Google Places POIs"
- **Large textarea** (3 rows, frosted glass `bg-white/10` style) with placeholder: *"e.g. Plan an 11-day Iceland Ring Road road trip starting from Nagpur, ₹3.5L budget, waterfalls & geothermal baths..."*
- **Row below textarea**: "Clear" button (if plan exists) + "Generate Itinerary" CTA button (`#0062e3`, bold)
- **Suggestion chips row** below: 4-5 horizontally scrollable pills with country flags:
  - 🇮🇸 Iceland Ring Road
  - 🇯🇵 Tokyo & Kyoto
  - 🇨🇭 Swiss Alps by Train
  - 🇮🇳 Varanasi & Rishikesh
  - 🇦🇺 Melbourne & Coast

---

### 2. Loading State (replaces results while generating)

White card with skeleton shimmer animation. Shows a **live agent progress ticker** cycling through realistic stages:
- "Orchestrator: Extracting destination, duration, budget..."
- "Destination Agent: Querying Google Places for attractions..."
- "Logistics Agent: Searching Skyscanner for flights & Booking.com for hotels..."
- "Budget Agent: Auditing totals against your budget ceiling..."
- "Review Agent: Validating pacing and coherence..."

Below the ticker: 3 skeleton stat cards in a row (shimmer blocks).

---

### 3. Results — Itinerary Header Banner

White card. Two-column layout:

**Left side:**
- Green pill badge: "✓ Review Status: PASS"
- Large bold title: "11-Day Iceland Ring Road Itinerary" (dynamically built from constraints)
- Subtitle: route summary like "Reykjavik → Vík → Akureyri → Reykjavik"

**Right side (stat block):**
- "Estimated Total Spend" label
- Large blue number: "₹3,12,000 INR"
- Green text below: "Within ₹3,50,000 budget"

**Below both columns:**
- Sky-blue tinted box with 💡 icon: "Strategic Routing Rationale: ..." (one paragraph explaining WHY this route works)

---

### 4. Flight Deals Section (conditional — shows for trips involving air travel)

**IMPORTANT**: This section appears for international trips, multi-city trips, and any trip where origin ≠ destination region. It does NOT appear for local trips like "Delhi to Varanasi" where trains/buses make more sense.

White card with ✈️ heading "Recommended Flight Deals (Skyscanner Live Data)"

Grid of 2-3 flight cards, each showing:
- Airline name + code (bold)
- Route: "NAG ⇄ KEF"
- Duration: "17.5 hrs total"
- Stops: "2 Stops via DEL, FRA"
- Price: "$890 per adult"
- Blue "View Deal" button (opens Skyscanner flights tab with prefilled search)

---

### 5. Car Rental Section (conditional — shows for ROAD TRIPS only)

**IMPORTANT**: This section appears ONLY when the trip is a road trip or self-drive (Iceland Ring Road, Great Ocean Road, Route 66, Rajasthan road trip, etc.). It does NOT appear for city trips or train journeys.

White card with 🚗 heading "Road Trip Car Rental" + amber "Calibrated Estimate" badge

Grid of 3 car options:
- Category label (Economy, Compact, SUV/4x4)
- Vehicle name: "Suzuki Vitara 4x4"
- Specs: "5 Seats · Automatic"
- Price: "$45/day" with "$495 total"
- Dark "Book Car" button linking to Skyscanner Car Hire

---

### 6. Transport Options Section (conditional — shows for REGIONAL/DOMESTIC trips)

**IMPORTANT**: This section appears for trips where road/rail/bus is more practical than flying. Examples: Delhi to Varanasi (train), Gangtok to Pelling in Sikkim (shared jeep), Bangkok to Chiang Mai (sleeper train).

White card with 🚆 heading "Getting There — Transport Options"

Shows 2-3 transport options as cards:
- **Train**: "Vande Bharat Express · Delhi → Varanasi · 8hrs · ₹1,800 · AC Chair Car"
- **Bus**: "UPSRTC Volvo · Delhi → Varanasi · 12hrs · ₹900 · Sleeper"
- **Flight** (if applicable): "IndiGo · DEL → VNS · 1.5hrs · ₹3,200"

Each card has a "Book" or "Check Availability" button.

---

### 7. Cost-Saving Tips (conditional — shows when budget agent generates tips)

Light emerald tinted card with 💰 heading "Cost Optimization Tips from Budget Agent"

Grid of 3 tip cards, each with:
- Bold title: "Book Guesthouses Over Hotels"
- Description text
- Green badge: "Save ₹8,000–12,000"

---

### 8. Day-by-Day Itinerary (the main content — always shows)

This is the most important section and it MUST adapt based on trip type.

**Section header**: "Day-by-Day Itinerary (With Real Stays & Attractions)" + "Click any day to expand"

Each day is a collapsible card. The collapsed state shows:
- Day badge: "D1" in a sky-blue rounded square
- City name in bold + mood tag pill (e.g. "Urban Discovery", "Scenic Drive", "Sacred Pilgrimage")
- One-line summary
- If road trip: amber driving pill "🚗 3.5 hrs to next stop"
- If mountain/trek: altitude indicator "⛰️ 1,650m → 2,200m"
- Chevron expand icon

**Expanded day content varies by trip type:**

#### Type A: Road Trip Day (Iceland, Great Ocean Road)
- Italic narrative paragraph: "Begin with the thundering Skógafoss..."
- **Driving Route Card**: From → To, distance, estimated time, road conditions
- **Today's Schedule**: Timeline of stops with time, name, notes, cost
- **Featured Sights (Google Places Verified)**: 2-column grid of attraction cards with ★ rating, hours, description
- **Tonight's Stay**: Hotel card with guest rating, neighborhood, price/night, "Book Stay" button

#### Type B: City/Cultural Day (Tokyo, Paris, Varanasi)
- Italic narrative: "Wake up before dawn for the unforgettable Ganga Aarti..."
- **Today's Schedule**: Timeline with tighter time slots (city days are packed)
  - For temple/sacred sites: Show opening hours prominently, dress code notes, best time to avoid crowds
  - For food spots: Show cuisine type, price band (₹/₹₹/₹₹₹), "locals recommend" tag
- **Featured Sights**: Attraction cards with ratings
- **Getting Around Today**: Metro/auto/walking card: "Walk 1.2km along the ghats" or "Metro: Shinjuku → Asakusa (35 min, ¥280)"
- **Tonight's Stay**: Hotel card

#### Type C: Mountain/Village-Hop Day (Sikkim, Ladakh, Nepal)
- Italic narrative: "The winding road to Pelling reveals Kanchenjunga..."
- **Today's Route Card**: Special format showing:
  - Start point → End point with altitude change
  - Road type: "Mountain highway, single lane after Ravangla"
  - Duration: "4.5 hrs (78 km)"
  - Permit required? Yes/No badge
- **Stops & Viewpoints**: Instead of a flat timeline, show a VERTICAL ROUTE with:
  - Pin markers: "📍 Tashiding Monastery (3,200m) · 30 min stop"
  - Pin markers: "📍 Kanchenjunga Viewpoint (2,800m) · Photo stop"
  - Pin markers: "📍 Pelling Market · Lunch stop"
- **Weather Alert**: Small amber card: "⚠️ Road may be foggy after 3 PM. Start early."
- **Tonight's Stay**: Homestay/guesthouse card (different styling — warmer, more personal)

#### Type D: Beach/Resort Day (Bali, Goa, Maldives)
- Italic narrative: "The morning light on Nusa Dua beach is golden..."
- **Today's Schedule**: Relaxed pacing — fewer slots, longer durations
  - Morning: Beach/water activity
  - Midday: Spa/rest (no activity — show "Free Time" slot)
  - Evening: Sunset spot + dinner
- **Water Activities Available**: Cards for snorkeling, surfing, diving with prices
- **Tonight's Stay**: Resort card with pool/beach access badges

#### Type E: Multi-City Transit Day (Europe backpacking, Japan rail)
- Italic narrative: "Board the Shinkansen at Tokyo Station for the 2h15m ride to Kyoto..."
- **Transit Card** (prominent, at top): Train/bus/flight between cities
  - Departure city, time → Arrival city, time
  - Duration, class, estimated cost
  - "💡 Buy JR Pass for ¥29,110 to cover all Shinkansen rides"
- **Afternoon Schedule**: Activities in the new city
- **Featured Sights**: Attractions in the arrival city
- **Tonight's Stay**: Hotel in the new city

---

### 9. Budget Matrix Section (always shows)

White card with "Itemized Budget Breakdown" heading.

**4-column grid of category stat tiles:**
- Stay: ₹1,20,000 INR
- Transport: ₹85,000 INR
- Food: ₹42,000 INR
- Activities: ₹35,000 INR

Each tile: light gray background, category label on top, big bold number, optional notes below.

**Below the grid (conditional)**: "Suggested Cost-Saving Swaps" — amber tinted rows showing:
- "Switch from Hotel Kría to Guesthouse Carina — Save ₹5,500/night"

---

### 10. Experience Highlights (optional — shows when the AI generates them)

White card with "✨ Trip Highlights" heading.

Horizontal scrollable row of highlight cards:
- "Golden Circle at Sunrise" — Day 2
- "Black Sand Beach Walk" — Day 4
- "Northern Lights from Akureyri" — Day 8

---

### 11. Error State (replaces results on failure)

Red-tinted card with exclamation icon:
- "Planning Request Encountered an Issue"
- Error message text
- "Retry Plan" red button

---

## Design Specifications

- **Canvas**: `#f1f3f8` light gray
- **Cards**: White, `border-radius: 24px`, subtle `border: 1px solid #e5e7eb`, `box-shadow: 0 1px 3px rgba(0,0,0,0.06)`
- **Primary CTA**: `#0062e3` (Skyscanner blue)
- **Dark sections**: `#02122c` (hero banner only)
- **Success/Budget**: Emerald green tints
- **Warning/Driving**: Amber tints
- **Error**: Red tints
- **Typography**: System font stack, heavy use of font-weight 800-900 for headings
- **Spacing**: Generous padding (24-32px in cards), 24px gap between cards
- **Mobile**: Stack all grids to single column, suggestion chips horizontally scroll, day cards full-width
- **No modal overlays** — everything is inline on the page

## Section Visibility Matrix (which sections show for which trip)

| Section | Iceland Road Trip | Tokyo+Kyoto | Delhi→Varanasi | Sikkim Circuit | Bali Beach |
|---------|:-:|:-:|:-:|:-:|:-:|
| Hero Input | ✅ | ✅ | ✅ | ✅ | ✅ |
| Itinerary Header | ✅ | ✅ | ✅ | ✅ | ✅ |
| Flight Deals | ✅ (international) | ✅ (international) | ❌ (domestic, train better) | ✅ (fly to Bagdogra) | ✅ (international) |
| Car Rental | ✅ (self-drive) | ❌ | ❌ | ❌ (shared jeep, not self-drive) | ❌ (scooter rental inline) |
| Transport Options | ❌ (car covers it) | ✅ (Shinkansen) | ✅ (train/bus primary) | ✅ (jeep/shared taxi) | ❌ |
| Cost-Saving Tips | ✅ | ✅ | ✅ | ✅ | ✅ |
| Day-by-Day | ✅ Type A | ✅ Type B+E | ✅ Type B | ✅ Type C | ✅ Type D |
| Budget Matrix | ✅ | ✅ | ✅ | ✅ | ✅ |
| Experience Highlights | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## FULL SCREEN MOCKUP 1: Iceland Ring Road (Road Trip — Type A)

> **Prompt used**: "Plan an 11-day Iceland Ring Road road trip starting from Nagpur, ₹3.5L budget, waterfalls & geothermal baths, love nature and scenic drives"

### Screen flow (top to bottom):

**[Hero Input Card]** — dark navy, textarea pre-filled with the prompt above, "Generate Itinerary" CTA active, suggestion chips below.

**[Itinerary Header Banner]**
- Badge: `✓ Review Status: PASS` (emerald green pill)
- Title: **"11-Day Iceland Ring Road Itinerary"**
- Route: `Reykjavik → Golden Circle → Vík → Höfn → Akureyri → Snæfellsnes → Reykjavik`
- Stat block: **₹3,12,400 INR** / Within ₹3,50,000 budget
- Strategic insight: "Counter-clockwise Ring Road routing avoids tourist bus convoys (which run clockwise), reaching popular South Coast waterfalls before 9 AM when parking is free and crowds are minimal."

**[Flight Deals Section]** ✈️
- 3 flight cards in a 2-column grid:
  - **IndiGo & Lufthansa / Icelandair** · NAG ⇄ KEF · 17.5 hrs · 2 Stops via DEL, FRA · **$890** · [View Deal]
  - **Air India & British Airways / Icelandair** · NAG ⇄ KEF · 18.5 hrs · 2 Stops via DEL, LHR · **$940** · [View Deal]
  - **Air Arabia & KLM / Icelandair** · NAG ⇄ KEF · 19.7 hrs · 2 Stops via SHJ, AMS · **$810** · [View Deal]

**[Car Rental Section]** 🚗 + amber "Calibrated Estimate" badge
- 3 car cards:
  - **Economy** · Hyundai i10 · 5 Seats · Manual · **$32/day** · $352 total · [Book Car]
  - **Compact SUV** · Suzuki Vitara · 5 Seats · Auto · **$45/day** · $495 total · [Book Car]
  - **4x4 Highland-Ready** · Dacia Duster 4WD · 5 Seats · Auto · **$68/day** · $748 total · [Book Car]

**[Cost-Saving Tips]** 💰 emerald card
- "Book N1 fuel stops" — "N1 stations offer loyalty discounts. Fill up at every station; remote areas have 100+ km gaps." — Save $40–60
- "Cook at guesthouses" — "Most Icelandic guesthouses have shared kitchens. Buy at Bónus supermarket (pink pig logo) instead of restaurants." — Save $300–500
- "Free hot springs" — "Skip Blue Lagoon ($85+). Visit free wild hot pots: Seljavallalaug, Reykjadalur, Hellulaug." — Save $85–170

**[Day-by-Day Itinerary]** — expanded Day 4 shown as example:

**Day 4 collapsed row:**
| D4 | **Vík** | 🏷️ "Coastal Wonder" | "Black sand beaches, basalt columns, and the thundering Skógafoss" | 🚗 2.5 hrs to Höfn | ▼ |

**Day 4 expanded:**

> *"Start early to catch Reynisfjara in solitude — the black sand absorbs morning light beautifully. The basalt columns form a natural cathedral. After lunch in Vík village, drive the stunning coastal stretch toward Höfn, watching for puffin colonies at Dyrhólaey."*

**Driving Route Card** (amber tinted, full width):
```
🚗  Vík → Höfn
    Distance: 275 km · Estimated: 3.5 hrs
    Road: Route 1 (paved, good condition)
    ⛽ Fuel stop recommended: Kirkjubæjarklaustur (halfway)
    ⚠️ Single-lane bridges — yield to oncoming traffic
```

**Today's Schedule:**
| Time | Activity | Notes | Cost |
|------|----------|-------|------|
| 07:00 | Reynisfjara Black Sand Beach | Arrive before tour buses. DANGER: Never turn back on waves | Free |
| 08:30 | Dyrhólaey Peninsula & Arch | 120m cliff views, puffins May–Aug | Free |
| 10:00 | Víkurkirkja (Vík Church) | Red-roofed hilltop church, panoramic photo spot | Free |
| 11:30 | Lunch at Suður-Vík Restaurant | Lamb soup + fresh bread, local favorite | ₹1,200 |
| 13:00 | Drive Vík → Höfn | Coastal scenic route, stop at Svartifoss if time | Fuel ₹800 |
| 17:00 | Check in at Höfn | Settle in, walk harbor | — |
| 19:00 | Dinner: Pakkhús Restaurant | Famous langoustine soup, harbor view | ₹2,500 |

**Featured Sights (Google Places Verified)** — 2-column grid:
- **Reynisfjara Black Sand Beach** · ★ 4.7 · 11,500 reviews · "World-renowned dramatic black volcanic sand beach featuring towering hexagonal basalt columns" · 🕒 Open 24 hours (Daylight recommended)
- **Dyrhólaey Peninsula & Arch** · ★ 4.8 · 6,200 reviews · "120m high promontory with gigantic natural black lava arch and puffin breeding colonies" · 🕒 Open 24 hours
- **Skógafoss Waterfall** · ★ 4.8 · 16,800 reviews · "Thundering 60m waterfall famous for persistent double rainbows on sunny days" · 🕒 Open 24 hours
- **Víkurkirkja** · ★ 4.6 · 2,100 reviews · "Picturesque red-roofed hillside church with panoramic coastal views" · 🕒 Mon 9–5

**Tonight's Stay** (sky-blue bordered card):
```
🏨  Tonight's Stay · Booking.com Real Inventory
    Hotel Kría                              $220/night
    ★ 9.0 Guest Score · Vik Center         [Book Stay →]
    Drangar Restaurant · Bar · Mountain Views
```

**[Budget Matrix]** — 4 stat tiles:
- Stay: ₹1,18,000 · Transport: ₹82,000 · Food: ₹45,000 · Activities: ₹32,000
- Swap: "Switch from Hotel Kría to Guesthouse Carina — Save ₹5,500/night"

---

## FULL SCREEN MOCKUP 2: Tokyo & Kyoto 5-Day (Multi-City Cultural — Type B+E)

> **Prompt used**: "Plan a 5-day trip to Japan: Tokyo + Kyoto, $3,000 budget. Authentic food and quiet morning temples, avoid heavy crowds."

### Screen flow:

**[Itinerary Header Banner]**
- Title: **"5-Day Tokyo & Kyoto Itinerary"**
- Route: `Tokyo (3 nights) → Shinkansen → Kyoto (2 nights)`
- Stat block: **$2,680 USD** / Within $3,000 budget
- Strategic insight: "Starting in Tokyo lets you acclimatize to the train system before Kyoto's more spread-out temple circuit. Visiting Fushimi Inari at 6 AM avoids the 10,000+ daily visitors — you'll have the first 500 torii gates nearly to yourself."

**[Flight Deals Section]** ✈️
- **Air India & ANA** · NAG ⇄ HND · 13.7 hrs · 1 Stop via DEL · **$680** · [View Deal]
- **IndiGo & Singapore Airlines** · NAG ⇄ HND · 14.3 hrs · 2 Stops via BOM, SIN · **$720** · [View Deal]

**[Transport Options Section]** 🚆 — THIS IS THE KEY DIFFERENTIATOR vs road trips
```
🚅  Inter-City Transit: Tokyo → Kyoto
    Shinkansen Nozomi · Tokyo Station → Kyoto Station
    Duration: 2 hrs 15 min · ¥13,320 (~$89)
    Class: Reserved Ordinary Car
    💡 Pro tip: Buy a 7-Day JR Pass (¥29,110) — covers this ride PLUS
       all JR lines in Tokyo and Kyoto. Saves ~$60 over individual tickets.
    [Check JR Pass →]
```

**[Day 3 Expanded — Transit Day]** (Type E: Multi-City Transit)

> *"Board the Shinkansen at Tokyo Station for the 2h15m ride to Kyoto. Watch Mount Fuji slide past on the right side (Seat E). Arrive at Kyoto Station and take the bus to Gion — you'll be walking Hanami-koji Lane by lunchtime."*

**Transit Card** (prominent, blue-tinted, at top of expanded day):
```
🚅  TOKYO → KYOTO
    Dep: Tokyo Station 09:33 → Arr: Kyoto Station 11:48
    Shinkansen Nozomi N700S · 2 hrs 15 min
    Reserved Seat · Car 7, Seat 14E (Mt. Fuji side)
    ¥13,320 ($89) · Covered by JR Pass
```

**Afternoon Schedule** (city activities after arrival):
| Time | Activity | Notes | Cost |
|------|----------|-------|------|
| 12:30 | Nishiki Market | "Kyoto's Kitchen" — 400m covered food street. Try dashi tamago, matcha warabi mochi | ¥1,500 |
| 14:30 | Kiyomizu-dera Temple | Wooden stage with city panorama. Less crowded after 2 PM. | ¥400 |
| 16:30 | Ninenzaka & Sannenzaka lanes | Photogenic stone-paved slopes. Tea houses. Buy pottery. | Free |
| 18:00 | Gion district walk | Watch for maiko (apprentice geisha) at dusk on Hanami-koji | Free |
| 19:30 | Dinner: Gion Kappa | Obanzai (Kyoto home cooking). Quiet, 8-seat counter. | ¥3,500 |

**Getting Around Today** (instead of driving card):
```
🚶 Walking: Kiyomizu area is best on foot (steep hills, narrow lanes)
🚌 Bus 206: Kyoto Station → Kiyomizu-michi (15 min, ¥230)
💡 Buy a Kyoto Bus 1-Day Pass (¥700) — unlimited rides, pays for itself in 4 trips
```

**[Day 1 Expanded — City Cultural Day]** (Type B)

> *"Land at Haneda and dive straight into Asakusa — Sensō-ji's Nakamise shopping street is alive by 10 AM, but the temple grounds are serenely empty at 6. Lunch on handmade soba in the backstreets, then lose yourself in Akihabara's electric maze."*

**Today's Schedule:**
| Time | Activity | Notes | Cost |
|------|----------|-------|------|
| 06:00 | Sensō-ji Temple (morning) | Grounds open at dawn. Main hall 6 AM. **Best time: before 7 AM** — near empty. Draw an omikuji fortune. | Free |
| 08:00 | Nakamise-dōri breakfast | Melon pan, ningyo-yaki, fresh senbei from stalls. | ¥600 |
| 09:30 | Meiji Jingu Shrine | Walk through the 170-acre forest. Serene even midday. | Free |
| 11:30 | Harajuku & Takeshita Street | Youth culture, crepe shops, vintage stores. 30-min walk-through. | ¥500 |
| 12:30 | Lunch: Fuunji Tsukemen | 🍜 Dipping ramen. Queue moves fast (~20 min). **Locals' #1 pick.** | ¥1,100 |
| 14:30 | teamLab Planets TOKYO | Barefoot immersive art. Book 2:30 PM slot online to skip queue. | ¥3,800 |
| 17:00 | Shibuya Scramble Crossing | Watch from Shibuya Sky or Starbucks 2F. Peak crossing at 5 PM. | Free |
| 19:00 | Dinner: Omoide Yokocho | 🍢 "Memory Lane" — tiny yakitori alleys near Shinjuku Station. Cash only. | ¥2,500 |

**Getting Around Today:**
```
🚃 Metro: Suica/Pasmo IC card — tap and ride all lines
   Asakusa → Meiji-Jingumae: Ginza Line + Chiyoda Line (35 min, ¥250)
   Harajuku → Toyosu (teamLab): Yamanote + Yurikamome (40 min, ¥380)
   Shibuya → Shinjuku: Yamanote Line (5 min, ¥150)
💡 Get Suica at any station kiosk. ¥500 deposit, recharge as you go.
```

**Featured Sights:**
- **Sensō-ji Temple** · ★ 4.5 · 68,000 reviews · "Tokyo's oldest Buddhist temple founded in 645 AD" · 🕒 Main Hall: 6 AM–5 PM
- **Meiji Jingu Shrine** · ★ 4.6 · 42,000 reviews · "Tranquil Shinto shrine in a 170-acre evergreen forest" · 🕒 Sunrise–Sunset
- **teamLab Planets** · ★ 4.6 · 31,000 reviews · "Immersive barefoot digital art museum" · 🕒 9 AM–10 PM · 💰💰💰
- **Shibuya Scramble** · ★ 4.5 · 45,000 reviews · "World's busiest intersection — 3,000 people per crossing" · 🕒 Open 24 hours

**Tonight's Stay:**
```
🏨  Tonight's Stay · Booking.com Real Inventory
    Hotel Gracery Shinjuku                  $185/night
    ★ 8.6 Guest Score · Kabukicho          [Book Stay →]
    Godzilla Head Terrace · Metro 5 min · Free WiFi
```

---

## FULL SCREEN MOCKUP 3: Sikkim Circuit (Mountain Village-Hop — Type C)

> **Prompt used**: "Plan a 7-day Sikkim trip from Delhi: Gangtok, Pelling, Lachung. ₹80,000 budget, monasteries and mountain views, first time in northeast India."

### Screen flow:

**[Itinerary Header Banner]**
- Title: **"7-Day Sikkim Mountain Circuit"**
- Route: `Delhi ✈ Bagdogra → Gangtok → Lachung → Pelling → Bagdogra ✈ Delhi`
- Stat block: **₹68,200 INR** / Within ₹80,000 budget
- Strategic insight: "Routing Gangtok → Lachung → Pelling (east to west) minimizes backtracking and lets you acclimatize gradually from 1,650m to 3,200m before the highest-altitude days. Lachung first would mean hitting 2,800m on Day 2 without adjustment."

**[Flight Deals Section]** ✈️
- **IndiGo** · DEL → IXB (Bagdogra) · 2.5 hrs · Direct · **₹4,200** · [View Deal]
- **Air India** · DEL → IXB · 2.5 hrs · Direct · **₹4,800** · [View Deal]

**[Transport Options Section]** 🚙 (NOT car rental — shared jeeps)
```
Getting Around Sikkim — Shared Jeep & Taxi Network

Unlike self-drive destinations, Sikkim's mountain roads require experienced
local drivers. All inter-city transport is via shared Sumo/Bolero jeeps or
private taxis booked through your hotel.

🚙 Bagdogra → Gangtok    Shared Jeep · 4.5 hrs · ₹350/seat
🚙 Gangtok → Lachung     Shared Jeep · 5 hrs · ₹400/seat (permit required)
🚙 Lachung → Pelling     Private Taxi · 8 hrs · ₹4,500 (via Gangtok transfer)
🚙 Pelling → Bagdogra    Shared Jeep · 5 hrs · ₹500/seat

⚠️ Permits: Lachung/Yumthang require Inner Line Permit (ILP).
   Your hotel in Gangtok can arrange this — allow 1 day processing.
   Carry 4 passport-size photos + ID photocopy.
```

**[Day 4 Expanded — Mountain Village-Hop Day]** (Type C)

> *"The winding road from Gangtok to Pelling is Sikkim's most spectacular drive — after crossing the Teesta River valley, the road climbs through cardamom plantations and prayer-flag-draped forests. At Ravangla, the 130-foot Tathagata Tsal Buddha statue appears suddenly against the Kanchenjunga range."*

**Today's Route Card** (special mountain format, amber + altitude):
```
⛰️  GANGTOK → PELLING via Ravangla
    Altitude: 1,650m → 2,150m (peak: 2,200m at Ravangla)
    Distance: 130 km · Duration: 5.5 hrs (mountain roads)
    Road: NH717A → Temi Tea Garden Road → Ravangla → Pelling
    Condition: Paved but narrow. Single-lane hairpins after Legship.
    ⚠️ Landslide-prone in monsoon (Jun–Sep). Check road status morning of.
    🚙 Transport: Private taxi recommended (₹3,500). Not suitable for shared jeep
       due to multiple viewpoint stops.
```

**Stops & Viewpoints** (VERTICAL ROUTE — not a flat table):
```
📍 09:00 · Gangtok (1,650m)
   │  Depart hotel. Pack lunch from hotel kitchen.
   │
   ↓  45 min drive · descend to Teesta River bridge
   │
📍 09:45 · Singtam Bridge Viewpoint
   │  Photo stop. Teesta-Rangit confluence visible below.
   │  ⏱️ 10 min stop
   │
   ↓  1.5 hr drive · climb through cardamom plantations
   │
📍 11:15 · Temi Tea Garden (1,800m)
   │  Walk through Sikkim's only tea estate. Buy organic
   │  Temi tea directly from the factory shop (₹200/100g).
   │  ⏱️ 30 min stop
   │
   ↓  1 hr drive · winding ascent
   │
📍 12:45 · Ravangla Buddha Park (2,200m) ← HIGHLIGHT
   │  130-foot Tathagata Tsal Buddha with Kanchenjunga backdrop.
   │  Meditation garden, prayer wheels. Best light: noon–2 PM.
   │  ⏱️ 1 hr stop · Lunch here (packed or at roadside Tibetan café)
   │  💰 Entry: ₹50
   │
   ↓  1.5 hr drive · descend to Legship, then climb to Pelling
   │
📍 15:30 · Pelling (2,150m)
   │  Check in. Rest. Walk to Pelling Helipad Viewpoint for
   │  golden-hour Kanchenjunga panorama (5 min walk, free).
   │
📍 17:00 · Sangachoeling Monastery
   │  One of Sikkim's oldest monasteries (1697). 20-min uphill
   │  walk through forest. Monks welcome visitors.
   │  ⏱️ 45 min · Free
   │
📍 19:00 · Dinner at hotel
   │  Dal-bhat-sabzi thali + momos (standard Sikkimese dinner)
   │  💰 ₹350
```

**Weather & Altitude Alert** (amber card):
```
⚠️ Altitude Notice
   Today's peak: 2,200m at Ravangla. Mild altitude — no acclimatization
   needed for most travelers. Drink extra water. Carry a light jacket;
   temperature drops ~6°C per 1,000m gained.

🌤️ Expected Weather: Partly cloudy, 12–18°C. Clear skies likely
   for Kanchenjunga views in afternoon.
```

**Tonight's Stay** (HOMESTAY style — warmer card, not corporate hotel):
```
🏡  Tonight's Stay · Local Homestay
    Kanchenjunga View Homestay              ₹1,800/night
    Host: Mrs. Doma Bhutia · Family-run     [Book via WhatsApp →]
    Home-cooked dinner included · Balcony with mountain view
    📍 Upper Pelling · 5 min walk to Helipad Viewpoint
    ⭐ Guest favorite: "Doma's thukpa and the sunrise from the
       balcony are worth the trip alone"
```

---

## FULL SCREEN MOCKUP 4: Delhi to Varanasi (Regional Pilgrimage — Type B, no flights)

> **Prompt used**: "Plan a 4-day Varanasi trip from Delhi, ₹25,000 budget, want to see all important ghats, temples, evening aarti, and try street food"

### Key UI differences from other trips:

**NO Flight Deals section** — train is the default and preferred transport for this route.

**NO Car Rental section** — Varanasi's old city is pedestrian-only; autos and boats are the transport.

**[Itinerary Header Banner]**
- Title: **"4-Day Varanasi Pilgrimage & Culture Itinerary"**
- Route: `Delhi → Varanasi (train) → Varanasi → Delhi (train)`
- Stat block: **₹18,400 INR** / Within ₹25,000 budget

**[Transport Options Section]** 🚆 (PRIMARY section — replaces flights)
```
🚆  Getting There — Delhi to Varanasi

RECOMMENDED:
🚅 Vande Bharat Express 22436
   New Delhi → Varanasi Junction
   Dep: 06:00 → Arr: 14:00 · 8 hrs
   AC Chair Car · ₹1,885
   💡 Book 60 days ahead on IRCTC — sells out fast
   [Check IRCTC →]

ALTERNATIVES:
🚂 Shiv Ganga Express 12560
   New Delhi → Varanasi Junction
   Dep: 19:00 → Arr: 05:30+1 · 10.5 hrs (overnight)
   AC 3-Tier Sleeper · ₹785
   💡 Saves a hotel night — arrive fresh at dawn for morning aarti

✈️ IndiGo / Air India
   DEL → VNS · 1.5 hrs · ₹3,200–4,800
   (Only if train sold out or time-constrained)
```

**[Day 2 Expanded — Pilgrimage/Cultural Day]** (Type B with sacred-site specifics)

> *"Wake before dawn. The pre-sunrise boat ride on the Ganges is Varanasi's most profound experience — watching the city come alive from the water as the first light catches the centuries-old ghats. No camera fully captures it. Just be present."*

**Today's Schedule:**
| Time | Activity | Notes | Cost |
|------|----------|-------|------|
| 04:30 | 🚣 Sunrise boat ride | Dashashwamedh → Manikarnika → Assi Ghat. **Book previous evening at ghat.** Shared boat ₹100/person, private ₹500. Go at 4:30 AM sharp — light changes fast. | ₹100–500 |
| 06:30 | Subah-e-Banaras (morning aarti) | At Assi Ghat. Smaller, more intimate than evening aarti. Sit on steps. | Free |
| 07:30 | Breakfast: Blue Lassi | 🥛 The legendary curd shop near Manikarnika. Try saffron or banana lassi. **Cash only, ₹40–80.** Queue is part of the charm. | ₹60 |
| 08:30 | Kashi Vishwanath Temple | 🛕 Holiest Shiva temple. **Dress code: No leather, cover shoulders/knees.** New corridor is spectacular. Free but long queue before 10 AM — go at 8:30. Photography prohibited inside. | Free |
| 10:30 | Walk: Manikarnika Ghat | Oldest cremation ghat. **Do not photograph.** Observe respectfully from above. Dom Raja's family has tended the eternal flame for centuries. | Free |
| 11:30 | Ghat walk: Manikarnika → Dashashwamedh | Walk along 84 ghats. Stop at Darbhanga Ghat (beautiful Rajasthani palace architecture). | Free |
| 12:30 | Lunch: Kachori Gali | 🍛 Famous lane near Vishwanath. Try kachori-sabzi (₹30) + jalebi (₹20). **Peak crowd 1–2 PM — go at 12:30.** | ₹150 |
| 14:00 | Sarnath (Buddhist site) | 🏛️ Where Buddha gave first sermon. Museum + Dhamek Stupa + Ashoka Pillar. Auto-rickshaw ₹200 round trip. **Museum closed Fridays.** | ₹30 entry |
| 16:30 | Return to ghats, rest/chai | Sit at Assi Ghat with chai (₹15) and watch the river | ₹15 |
| 18:30 | 🔥 Ganga Aarti (evening) | Dashashwamedh Ghat. **THE must-see.** Arrive 30 min early for front-row ghat steps. Or watch from a boat (₹150) for full panoramic view. 7 priests, fire rituals, chanting — runs ~45 min. | Free (boat ₹150) |
| 20:00 | Dinner: Baati Chokha | 🍛 Rooftop restaurant near Assi. Litti-chokha, baigan bharta, thandai. Great Ganga view. | ₹350 |

**Getting Around Today:**
```
🚶 Walking: Ghat area is pedestrian-only. Wear comfortable shoes —
   stone steps are uneven and slippery near water.
🛺 Auto-rickshaw: ₹50–100 within old city. ₹200 to Sarnath (10 km).
   Always fix fare before boarding. Don't use meter — they inflate.
🚣 Boat: Shared ₹100/person, Private ₹500–800/hr.
   Book at Dashashwamedh Ghat. Bargain firmly.
💡 Varanasi tip: The old city lanes are a labyrinth. Getting lost IS
   the experience. Ask any local "Dashashwamedh?" and follow pointing fingers.
```

**Tonight's Stay:**
```
🏨  Tonight's Stay · Booking.com Real Inventory
    Zostel Varanasi                         ₹800/night
    ★ 8.9 Guest Score · Assi Ghat          [Book Stay →]
    Rooftop café · Ganga view · 3 min walk to Assi Ghat
    💡 Budget pick: Best hostel in Varanasi. Private room ₹1,600.
```

---

## What Makes Each Trip Type's UI Feel Different — Summary for Stitch

| Element | Road Trip | City/Cultural | Mountain | Beach | Transit Day |
|---------|-----------|---------------|----------|-------|-------------|
| **Day card accent** | Amber driving pill | Purple mood tag | Green altitude badge | Teal wave icon | Blue transit badge |
| **Top of expanded day** | Driving Route Card | Getting Around (metro/walking) | Vertical Route with pins | "Today's Vibe" relaxed card | Transit Card (train/bus) |
| **Schedule density** | 5–6 stops spread across drive | 8–10 packed activities | 4–5 stops along route | 3–4 leisurely activities | 2–3 activities in new city |
| **Key info callout** | Road conditions, fuel stops | Temple hours, dress codes, crowd tips | Altitude, permits, weather | Tide times, water activity availability | Departure/arrival times, pass tips |
| **Accommodation style** | Guesthouse/hostel cards | Hotel with metro distance | Homestay (warm, personal) | Resort with amenity badges | Hotel in arrival city |
| **Transport visualization** | Route distance + driving time | Metro line + walking distance | Vertical pin-to-pin route | Scooter/taxi estimate | Departure → Arrival card |

---

## Mobile-Specific Notes for Stitch

- **Suggestion chips**: Horizontal scroll, no wrap. Each chip ~120px wide.
- **Flight/car/transport cards**: Stack to single column below 640px.
- **Day cards**: Full-width. Collapsed state must fit in ~80px height.
- **Vertical route (mountain type)**: Left-aligned pin markers with connecting dotted line. Works naturally on mobile.
- **Budget matrix**: 2x2 grid on mobile instead of 4-column.
- **Tonight's Stay card**: Stack image above text on mobile.
- **Touch targets**: All buttons minimum 44x44px tap area.
- **Sticky hero**: On mobile, the hero input card scrolls away (NOT sticky) to maximize result area.
