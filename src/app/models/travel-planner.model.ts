/**
 * TypeScript Data Models for Skyscanner AI Travel Planner
 * Matching schemas in backend/app/models/schemas.py (Phases 4-6).
 */

export interface RealFlightOffer {
  id: string;
  airline: string;
  airline_code?: string;
  airline_logo?: string | null;
  flight_number?: string | null;
  origin: string;
  destination: string;
  price: number;
  currency: string;
  duration_minutes: number;
  stops: number;
  layover_airports?: string[];
  departure: string;
  arrival: string;
  is_greener?: boolean;
  deeplink?: string | null;
}

export interface RealHotelOffer {
  id: string;
  name: string;
  city: string;
  price_per_night: number;
  total_price?: number;
  currency: string;
  star_rating?: number | null;
  guest_rating?: number | null;
  review_count?: number | null;
  address?: string | null;
  neighborhood?: string | null;
  image_url?: string | null;
  deeplink?: string | null;
  amenities?: string[];
}

export interface CarEstimate {
  id: string;
  supplier: string;
  vehicle_name: string;
  category: string;
  price_per_day: number;
  total_price: number;
  currency: string;
  seats: number;
  transmission: string;
  is_estimate: boolean;
  deeplink?: string | null;
}

export interface PlaceInfo {
  id?: string;
  name: string;
  place_id?: string | null;
  rating?: number | null;
  review_count?: number | null;
  types?: string[];
  opening_hours?: string[] | null;
  open_now?: boolean | null;
  address?: string | null;
  city?: string | null;
  lat?: number | null;
  lng?: number | null;
  photo_url?: string | null;
  price_level?: number | null;
  description?: string | null;
  website?: string | null;
  google_maps_url?: string | null;
  coordinates?: { lat: number; lng: number } | null;
}

export interface MapPin {
  id: string;
  label: string;
  lat: number;
  lng: number;
  day_number?: number | null;
  pin_type: 'overnight' | 'attraction' | 'transit' | 'airport';
  description?: string | null;
}

export interface CostSavingTip {
  id: string;
  title: string;
  description: string;
  category?: string | null;
  estimated_savings?: string | null;
}

export interface SuggestedSwap {
  original_item: string;
  suggested_alternative: string;
  savings_estimate: number;
  rationale: string;
}

export interface BudgetViolation {
  category: string;
  estimated: number;
  limit: number;
  over_by: number;
}

export interface BudgetCategory {
  category: 'stay' | 'transport' | 'food' | 'activities' | 'buffer';
  estimated_total: number;
  currency: string;
  breakdown?: Record<string, number> | null;
  notes?: string | null;
}

export interface BudgetBreakdown {
  categories: BudgetCategory[];
  grand_total: number;
  currency: string;
  within_budget?: boolean;
  remaining_buffer?: number;
  violations?: BudgetViolation[];
  suggested_swaps?: SuggestedSwap[];
  flags?: string[];
}

export interface DayItineraryItem {
  slot_index: number;
  time: string;
  activity_id?: string | null;
  activity_name: string;
  city?: string;
  type?: string;
  cost_estimate: number;
  travel_time_from_prev?: string | null;
  notes?: string | null;
}

export interface DayItinerary {
  day_number: number;
  city: string;
  items: DayItineraryItem[];
  day_summary: string;
  day_cost: number;
  lodging_area?: string | null;
  mood?: string | null;
  highlight?: string | null;
  day_narrative?: string | null;
  hotel_options?: RealHotelOffer[];
  places?: PlaceInfo[];
  driving_time_to_next?: string | null;
}

export interface TravelConstraints {
  origin?: string | null;
  origin_city?: string | null;
  start_date?: string | null;
  destination_region?: string | null;
  cities: string[];
  duration_days: number;
  budget_total: number;
  currency: string;
  budget_tier?: string | null;
  preferences: string[];
  avoidances: string[];
  is_road_trip: boolean;
}

export interface ExperienceHighlight {
  title: string;
  description: string;
  day_number?: number | null;
}

export interface TransportSegment {
  id: string;
  from_city: string;
  to_city: string;
  recommended_mode: 'flight' | 'train' | 'bus' | 'drive' | 'ferry';
  reason: string;
  estimated_duration_hours: number;
  estimated_cost_usd: number;
  operator_name?: string | null;
  line_or_flight_number?: string | null;
  booking_url?: string | null;
}

export interface FinalItinerary {
  id: string;
  constraints: TravelConstraints;
  days: DayItinerary[];
  neighborhoods: Record<string, string[]>;
  logistics_summary: string;
  strategic_insight?: string | null;
  budget_analysis?: string | null;
  cost_optimization_tips: string[];
  cost_saving_tips_v2?: CostSavingTip[];
  flight_options?: RealFlightOffer[];
  transport_segments?: TransportSegment[];
  car_estimates?: CarEstimate[];
  map_pins?: MapPin[];
  why_this_plan?: string | null;
  what_not_to_do?: string[];
  base_selection_rationale?: Record<string, string>;
  experience_highlights?: ExperienceHighlight[];
  best_time_to_visit?: string | null;
  budget_rollup: BudgetBreakdown;
  review_status: 'pass' | 'warnings' | 'fail' | 'approved';
  review_warnings?: string[];
  disclaimer?: string;
  generated_at?: string;
}

export interface PlanRequest {
  request: string;
  stub_mode?: boolean;
  origin_city?: string;
  start_date?: string;
  currency?: string;
}

export interface PlanResponse {
  final_itinerary: FinalItinerary;
  constraints: TravelConstraints;
  review_summary: string;
  trace_id: string;
  processing_time_ms?: number;
  used_stub_mode: boolean;
}

