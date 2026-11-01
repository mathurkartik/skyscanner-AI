---
name: Horizon Travel System
colors:
  surface: '#f7f9fe'
  surface-dim: '#d8dadf'
  surface-bright: '#f7f9fe'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f9'
  surface-container: '#eceef3'
  surface-container-high: '#e6e8ed'
  surface-container-highest: '#e0e2e7'
  on-surface: '#181c20'
  on-surface-variant: '#424654'
  inverse-surface: '#2d3135'
  inverse-on-surface: '#eff1f6'
  outline: '#727786'
  outline-variant: '#c2c6d7'
  surface-tint: '#0057cc'
  primary: '#004bb2'
  on-primary: '#ffffff'
  primary-container: '#0062e3'
  on-primary-container: '#e5eaff'
  inverse-primary: '#b0c6ff'
  secondary: '#505f7c'
  on-secondary: '#ffffff'
  secondary-container: '#cbdafd'
  on-secondary-container: '#515f7d'
  tertiary: '#005c54'
  on-tertiary: '#ffffff'
  tertiary-container: '#00776d'
  on-tertiary-container: '#85ffef'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d9e2ff'
  primary-fixed-dim: '#b0c6ff'
  on-primary-fixed: '#001945'
  on-primary-fixed-variant: '#00419c'
  secondary-fixed: '#d7e2ff'
  secondary-fixed-dim: '#b8c7e9'
  on-secondary-fixed: '#0b1b35'
  on-secondary-fixed-variant: '#384763'
  tertiary-fixed: '#7af7e7'
  tertiary-fixed-dim: '#5bdacb'
  on-tertiary-fixed: '#00201d'
  on-tertiary-fixed-variant: '#005049'
  background: '#f7f9fe'
  on-background: '#181c20'
  surface-variant: '#e0e2e7'
typography:
  display-hero:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '900'
    lineHeight: 48px
    letterSpacing: -0.03em
  display-hero-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '900'
    lineHeight: 34px
    letterSpacing: -0.025em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '800'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '800'
    lineHeight: 30px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '800'
    lineHeight: 26px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '700'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-lg-bold:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '700'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-md-bold:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  body-sm-bold:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
  label-badge:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.04em
  price-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '900'
    lineHeight: 28px
    letterSpacing: -0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-mobile: 0.75rem
  margin: 1.5rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

This design system establishes a high-clarity, utility-first travel metasearch experience optimized for mobile interfaces while scaling effortlessly to desktop. It balances utilitarian travel data (airports, layovers, durations, pricing) with an optimistic, reassuring aesthetic.

The visual style blends **Corporate / Modern** clarity with **Tactile Softness**:
- **Utilitarian & Grounded:** Clean contrast, immediate scanability of complex travel itineraries, and friction-free interaction models.
- **Deep Immersion:** Anchored by an authoritative midnight navy canvas in headers and hero search modules, transitioning into an airy, cloud-like neutral foundation for search results and cards.
- **Decisive Wayfinding:** High-energy electric blues paired with deliberate emerald and amber functional accents ensure rapid comprehension of pricing, ratings, and operational notices.

## Colors

The palette is engineered around instant contrast and cognitive ease in high-density data environments.

### Primary Roles
- **Hero & Header Surface (`#02122c`):** Deep Navy. Provides grounding weight to search bars, status headers, and navigation bars. Text on this surface must strictly use pure white `#ffffff` or high-contrast muted tint `#94a3b8`.
- **Primary Action (`#0062e3`):** High-saturation blue dedicated to primary CTAs (e.g., "Search flights", "Select deal", "Continue"). Never diluted with competing saturated blues.
- **Canvas Base (`#f1f3f8`):** Off-cool grey canvas that sets apart pure white content cards without harsh visual glare.

### Functional Accents
- **Positive & Value (`#00a698`):** Emerald green used selectively for great prices, cheapest flight badges, positive review scores (e.g., "8.8 Superb"), and eco-friendly flight tags.
- **Warning & Attention (`#d97706` / `#b45309`):** Amber accent designated for critical transit steps, layover warnings, self-transfer flags, and time-sensitive fare alerts.
- **Surface Borders (`#e5e7eb`):** Neutral gray border defining card edges against the canvas.

## Typography

Typography relies entirely on **Inter** to ensure maximum legibility at small sizes and high rendering performance across platforms.

- **Weight Contrast:** Headings and prices use intense weights (`800` Extra Bold and `900` Black) with tighter tracking (`-0.015em` to `-0.03em`) to create definitive visual impact.
- **Flight & Numeric Legibility:** Time readouts (e.g., `14:25 - 17:50`), durations, and prices employ `Inter` tabular figures (`tnum`) where appropriate to ensure vertical alignment in list views.
- **Micro-labels:** Badges, warnings, and metadata labels use uppercase or heavy-weight condensed tokens (`label-badge`) to maintain visibility at small scales.

## Layout & Spacing

The layout is architected around a fluid, touch-optimized vertical stack for mobile, transitioning to a structured 12-column grid on desktop.

### Breakpoints & Canvas
- **Mobile (< 768px):** Single-column vertical stream. Margin is set to `1rem` (`margin-mobile`), gutter is `0.75rem` (`gutter-mobile`). The navy hero collapses cleanly behind sticky origin/destination filters.
- **Tablet (768px - 1024px):** 8-column layout. Margin expands to `1.5rem`. Search controls transition into a two-tiered floating bar.
- **Desktop (> 1024px):** 12-column layout with a fixed max-width container of `1200px`. Left rail (3 columns) hosts filter panels; main content (9 columns) accommodates flight and hotel deal cards.

### Layout Rhythms
- **Component Padding:** Standard card interior padding is `1rem` on mobile, increasing to `1.5rem` on tablet/desktop.
- **Stacking Spacing:** Flight result cards separate by `0.75rem` on mobile and `1rem` on desktop to maintain clean grouping without fragmenting the scroll flow.

## Elevation & Depth

This system intentionally suppresses aggressive elevation layers, relying on crisp surface containment and subtle depth:

- **Surface Tiers:**
  1. *Level 0 (Canvas):* Light grey (`#f1f3f8`).
  2. *Level 1 (Card & Content Blocks):* Pure white (`#ffffff`) bordered by `1px solid #e5e7eb`. Soft ambient shadow: `0 1px 3px rgba(0, 0, 0, 0.06)`.
  3. *Level 2 (Floating Action Panels & Bottom Sheets):* Solid white elevated with `0 8px 24px rgba(2, 18, 44, 0.12)`.
  4. *Hero Overlays:* Solid deep navy (`#02122c`) surfaces do not use drop shadows; they anchor to the top edge and define physical hierarchy through contrast.
- **Tactile Feedback:** Cards interactive upon hover or active press do not elevate further; they transition border-color to `#0062e3` or show subtle scaling feedback (`transform: translateY(-1px)`).

## Shapes

The design system uses deliberate geometry to balance friendly accessibility with compact data efficiency:

- **Primary Cards:** Strict `24px` border radius (`rounded-xl` equivalent). This prominent radius defines the signature friendly feel of all travel result cards and search forms.
- **Action Buttons & Inputs:** `12px` to `16px` radius (`rounded-md` / `rounded-lg`) to preserve internal tappable area without wasting horizontal space.
- **Badges & Category Chips:** Fully pill-shaped (`9999px`) to create clear differentiation between actionable inputs and status indicators.

## Components

### Buttons
- **Primary CTA:** Background `#0062e3`, text `#ffffff`, border radius `12px`, font `body-lg-bold`. Min-height `48px` on mobile for optimal tap ergonomics. Active state: `#004bb3`.
- **Secondary CTA:** Pure white background, `1.5px solid #0062e3`, text `#0062e3`, font `body-lg-bold`.
- **Tertiary / Utility:** Transparent background, text `#0062e3` or `#02122c`, no border, padded with `space-sm`.

### Travel Deal Cards
- **Card Structure:** White background (`#ffffff`), `24px` radius, `1px solid #e5e7eb`, shadow `0 1px 3px rgba(0,0,0,0.06)`. Padded with `1rem` on mobile, `1.25rem` on desktop.
- **Itinerary Segments:** Carrier logo (32x32px), flight times in `headline-sm`, airport codes in `body-sm` muted grey, duration line centered with stopover indicator.
- **Price Block:** Aligned bottom-right or separated bottom row on mobile. Uses `price-lg` font in `#02122c` accompanied by micro text "per traveler".

### Chips & Filter Pills
- **Unselected:** Background `#ffffff`, border `1px solid #e5e7eb`, text `#02122c`, pill-shaped (`9999px`), padding `0.5rem 1rem`.
- **Selected:** Background `#02122c`, border `1px solid #02122c`, text `#ffffff`.
- **Functional Chips (Cheapest / Best):** Background `#e6f6f4`, text `#00a698`, border `1px solid rgba(0, 166, 152, 0.2)`.

### Form & Input Fields
- **Search Inputs (Origin / Destination / Dates):** Embedded in white cards or navy hero modules. Height `52px`, `12px` border radius, `1px solid #e5e7eb`, font `body-lg`. Focus ring: `2px solid #0062e3` with no offset.
- **Date / Guest Selectors:** Segmented cards with bold value preview (`headline-sm`) and small uppercase category labels (`label-badge`).

### Selection Controls (Checkboxes & Radios)
- **Checkboxes:** `20px x 20px`, `6px` radius, border `2px solid #cbd5e1`. Checked: background `#0062e3`, border `#0062e3`, white checkmark icon.
- **Radio Buttons:** `20px x 20px`, circular. Checked: `#0062e3` outer ring with white inset and solid blue center dot.

### Specialized Travel Badges & Indicators
- **Review Rating Badges:** Pill-shaped, background `#00a698`, text `#ffffff`, font `body-sm-bold`, padding `0.25rem 0.5rem`.
- **Warning Callouts (Self-transfer, long layover):** Background `#fef3c7`, border `1px solid #fde68a`, text `#92400e`, icon `#d97706`, radius `12px`.