export interface HotelOffer {
  id: string;
  name: string;
  city: string;
  country: string;
  neighborhood: string;
  distanceFromCenterKm: number;
  starRating: number;
  guestRating: number;
  reviewCount: number;
  ratingLabel: string;
  pricePerNightUSD: number;
  totalPriceUSD: number;
  imageUrl: string;
  freeCancellation: boolean;
  breakfastIncluded: boolean;
  freeWifi: boolean;
  pool: boolean;
  provider: string;
}

export interface CarOffer {
  id: string;
  name: string;
  category: 'Small' | 'Medium' | 'Large' | 'SUV' | 'Luxury' | 'Electric';
  supplier: string;
  supplierLogo: string;
  pricePerDayUSD: number;
  totalPriceUSD: number;
  seats: number;
  doors: number;
  bags: number;
  transmission: 'Automatic' | 'Manual';
  airConditioning: boolean;
  unlimitedMileage: boolean;
  freeCancellation: boolean;
  rating: number;
  imageUrl: string;
}

export interface ExploreDestination {
  id: string;
  city: string;
  country: string;
  airportCode: string;
  priceFromUSD: number;
  flightType: 'Direct' | '1 Stop';
  imageUrl: string;
  tag: string;
  popularMonth: string;
}

