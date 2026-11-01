import '@angular/compiler';
import { describe, it, expect, beforeEach } from 'vitest';
import { CurrencyService, SUPPORTED_CURRENCIES } from './services/currency.service';
import { FlightService } from './services/flight.service';
import { FavoritesService } from './services/favorites.service';
import { SkyscannerApiService } from './services/skyscanner-api.service';
import { POPULAR_AIRPORTS } from './data/airports.data';
import { generateFlightsForRoute } from './data/flights.data';
import { HOTELS_DATA, CARS_DATA, EXPLORE_DESTINATIONS } from './data/travel.data';
import { SKYSCANNER_FAQS, INTERNATIONAL_SITES } from './data/faq.data';
import { createEnvironmentInjector } from '@angular/core';

if (typeof localStorage === 'undefined') {
  let store: Record<string, string> = {};
  (globalThis as any).localStorage = {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; }
  };
}

describe('Skyscanner Multi-Module Test Suite', () => {

  describe('Module 1: Currency & Localization Service', () => {
    let service: CurrencyService;

    beforeEach(() => {
      localStorage.clear();
      service = new CurrencyService();
    });

    it('should initialize with USD default currency', () => {
      expect(service.selectedCurrency().code).toBe('USD');
      expect(service.selectedCurrency().symbol).toBe('$');
    });

    it('should support EUR, GBP, JPY, INR, CAD, AUD', () => {
      const codes = SUPPORTED_CURRENCIES.map(c => c.code);
      expect(codes).toContain('EUR');
      expect(codes).toContain('GBP');
      expect(codes).toContain('JPY');
      expect(codes).toContain('INR');
      expect(codes).toContain('CAD');
      expect(codes).toContain('AUD');
    });

    it('should accurately convert and format amounts in selected currency', () => {
      service.setCurrency('EUR');
      expect(service.selectedCurrency().code).toBe('EUR');
      const formatted = service.format(100);
      expect(formatted).toContain('€');

      service.setCurrency('INR');
      expect(service.selectedCurrency().code).toBe('INR');
      expect(service.format(100)).toContain('₹');
    });
  });

  describe('Module 2: Flight Search & Realistic Routing Engine', () => {
    let flightService: FlightService;

    beforeEach(() => {
      const injector = createEnvironmentInjector([SkyscannerApiService, FlightService], null as any);
      flightService = injector.get(FlightService);
    });

    it('should include Reykjavik (KEF and RKV) in airport database', () => {
      const reykjavikAirports = POPULAR_AIRPORTS.filter(a => a.city.toLowerCase().includes('reykjavik'));
      expect(reykjavikAirports.length).toBeGreaterThanOrEqual(2);
      expect(reykjavikAirports.some(a => a.code === 'KEF')).toBe(true);
      expect(reykjavikAirports.some(a => a.code === 'RKV')).toBe(true);
    });

    it('should accurately route Nagpur (NAG) to Melbourne (MEL) without British Airways or Delta', () => {
      const nagpur = POPULAR_AIRPORTS.find(a => a.code === 'NAG')!;
      const melbourne = POPULAR_AIRPORTS.find(a => a.code === 'MEL')!;
      const flights = generateFlightsForRoute(nagpur, melbourne, '2026-11-05', '2026-11-22', 'economy', 1);

      expect(flights.length).toBeGreaterThan(0);
      const airlines = flights.map(f => f.outbound.airline);
      
      // Should NOT have Delta or British Airways originating in Nagpur
      expect(airlines.includes('Delta Air Lines')).toBe(false);
      expect(airlines.includes('British Airways')).toBe(false);

      // Should have authentic carriers (Qantas, Singapore Airlines, Malaysia Airlines, Emirates)
      expect(airlines.some(a => a.includes('Qantas') || a.includes('Singapore') || a.includes('Malaysia') || a.includes('Emirates'))).toBe(true);

      // First leg must be domestic Indian carrier (IndiGo or Air India) or Air Arabia
      flights.forEach(f => {
        expect(f.outbound.segments.length).toBeGreaterThanOrEqual(2);
        const leg1Carrier = f.outbound.segments[0].airline;
        expect(['IndiGo', 'Air India', 'Air Arabia'].includes(leg1Carrier)).toBe(true);
      });
    });

    it('should realistically route from Nagpur (NAG) to Singapore (SIN) via BOM/DEL on IndiGo or Singapore Airlines', () => {
      const nagpur = POPULAR_AIRPORTS.find(a => a.code === 'NAG')!;
      const singapore = POPULAR_AIRPORTS.find(a => a.code === 'SIN')!;
      const flights = generateFlightsForRoute(nagpur, singapore, '2026-11-15', '2026-11-22', 'economy', 1);

      expect(flights.length).toBeGreaterThan(0);
      const airlines = flights.map(f => f.outbound.airline);
      expect(airlines.some(a => a.includes('IndiGo') || a.includes('Singapore') || a.includes('Air India'))).toBe(true);

      // Verify realistic layover hubs
      const layovers = flights.flatMap(f => f.outbound.stops);
      expect(layovers.some(h => ['BOM', 'DEL', 'SHJ', 'DXB'].includes(h))).toBe(true);
    });

    it('should filter flights by stops and airlines', () => {
      flightService.updateFilter({ stops: [1] });
      const filtered = flightService.filteredFlights();
      filtered.forEach(f => {
        expect(f.outbound.stopsCount).toBe(1);
      });
    });

    it('should toggle price alerts correctly', () => {
      expect(flightService.priceAlertActive()).toBe(false);
      flightService.togglePriceAlert();
      expect(flightService.priceAlertActive()).toBe(true);
    });
  });

  describe('Module 3: Live Skyscanner API Service Configuration', () => {
    let apiService: SkyscannerApiService;

    beforeEach(() => {
      localStorage.clear();
      apiService = new SkyscannerApiService();
    });

    it('should allow setting and persisting RapidAPI Key', () => {
      expect(apiService.apiKey()).toBe('');
      expect(apiService.isLiveMode()).toBe(false);

      apiService.setApiKey('test-rapidapi-key-12345');
      expect(apiService.apiKey()).toBe('test-rapidapi-key-12345');
      expect(apiService.isLiveMode()).toBe(true);
      expect(localStorage.getItem('skyscanner_rapidapi_key')).toBe('test-rapidapi-key-12345');
    });
  });

  describe('Module 4: Favorites & Watchlist Service', () => {
    let service: FavoritesService;

    beforeEach(() => {
      localStorage.clear();
      service = new FavoritesService();
    });

    it('should save and remove flights from watchlist with localStorage persistence', () => {
      expect(service.isFlightSaved('fl-test-123')).toBe(false);
      service.toggleFlight('fl-test-123');
      expect(service.isFlightSaved('fl-test-123')).toBe(true);
      expect(service.savedList()).toContain('fl-test-123');

      service.toggleFlight('fl-test-123');
      expect(service.isFlightSaved('fl-test-123')).toBe(false);
    });
  });

  describe('Module 5: Hotels & Accommodation Module', () => {
    it('should have verified hotel inventory with guest ratings and amenities', () => {
      expect(HOTELS_DATA.length).toBeGreaterThan(0);
      HOTELS_DATA.forEach(hotel => {
        expect(hotel.name).toBeTruthy();
        expect(hotel.starRating).toBeGreaterThanOrEqual(3);
        expect(hotel.guestRating).toBeGreaterThan(8.0);
        expect(hotel.pricePerNightUSD).toBeGreaterThan(0);
      });
    });
  });

  describe('Module 6: Car Hire Module', () => {
    it('should provide rental options across multiple vehicle categories', () => {
      expect(CARS_DATA.length).toBeGreaterThan(0);
      const categories = CARS_DATA.map(c => c.category);
      expect(categories).toContain('Small');
      expect(categories).toContain('SUV');
      expect(categories).toContain('Electric');
      expect(categories).toContain('Luxury');
    });
  });

  describe('Module 7: Explore Everywhere Module', () => {
    it('should offer curated destination cards with flight prices', () => {
      expect(EXPLORE_DESTINATIONS.length).toBeGreaterThanOrEqual(6);
      EXPLORE_DESTINATIONS.forEach(dest => {
        expect(dest.city).toBeTruthy();
        expect(dest.priceFromUSD).toBeGreaterThan(0);
      });
    });
  });

  describe('Module 8: Skyscanner FAQs & International Sites', () => {
    it('should contain 10 Skyscanner FAQs across 2 columns matching screenshot', () => {
      expect(SKYSCANNER_FAQS.length).toBe(10);
      expect(SKYSCANNER_FAQS[0].question).toBe('How does Skyscanner work?');
      expect(SKYSCANNER_FAQS[9].question).toBe('Can I book flights that emit less CO₂?');
    });

    it('should list international country domains matching screenshot', () => {
      expect(INTERNATIONAL_SITES.length).toBeGreaterThanOrEqual(10);
      const countries = INTERNATIONAL_SITES.map(s => s.name);
      expect(countries).toContain('India');
      expect(countries).toContain('United States');
      expect(countries).toContain('United Kingdom');
    });
  });

});
