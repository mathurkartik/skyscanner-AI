export interface Airport {
  code: string;
  name: string;
  city: string;
  country: string;
}

export type TripType = 'round-trip' | 'one-way' | 'multi-city';
export type CabinClass = 'economy' | 'premium_economy' | 'business' | 'first';
export type SortOption = 'best' | 'cheapest' | 'fastest';

export interface SearchQuery {
  tripType: TripType;
  origin: Airport;
  destination: Airport;
  departDate: string;
  returnDate: string;
  adults: number;
  children: number;
  cabinClass: CabinClass;
  directOnly: boolean;
}

export interface FlightSegment {
  flightNumber: string;
  airline: string;
  airlineCode: string;
  airlineLogo: string;
  aircraft: string;
  originCode: string;
  originCity: string;
  originAirport: string;
  destinationCode: string;
  destinationCity: string;
  destinationAirport: string;
  departureTime: string;
  arrivalTime: string;
  durationMinutes: number;
  layoverDurationMinutes?: number;
  layoverCity?: string;
  layoverAirportCode?: string;
}

export interface FlightLeg {
  id: string;
  departureTime: string;
  arrivalTime: string;
  originCode: string;
  destinationCode: string;
  originCity: string;
  destinationCity: string;
  durationMinutes: number;
  stopsCount: number;
  stops: string[];
  airline: string;
  airlineCode: string;
  airlineLogo: string;
  flightNumber: string;
  overnight: boolean;
  segments: FlightSegment[];
}

export interface BookingProvider {
  name: string;
  logo: string;
  priceUSD: number;
  rating: number;
  reviewCount: number;
  isDirectAirline?: boolean;
}

export interface FlightOffer {
  id: string;
  outbound: FlightLeg;
  inbound?: FlightLeg;
  priceUSD: number;
  cabinClass: CabinClass;
  co2ReductionPercent?: number; // e.g. 24% less CO2 than average
  cheapest?: boolean;
  fastest?: boolean;
  best?: boolean;
  baggage: {
    personalItem: boolean;
    carryOn: boolean;
    checkedBagCount: number;
  };
  providers: BookingProvider[];
}

export interface FlightFilterState {
  stops: number[]; // e.g. [0, 1, 2]
  airlines: string[];
  maxPriceUSD: number;
  maxDurationMinutes: number;
  departureTimeRange: 'all' | 'morning' | 'afternoon' | 'evening';
  greenerChoiceOnly: boolean;
}

