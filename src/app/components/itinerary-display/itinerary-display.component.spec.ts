import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ItineraryDisplayComponent } from './itinerary-display.component';
import { FinalItinerary } from '../../models/travel-planner.model';

describe('ItineraryDisplayComponent', () => {
  let component: ItineraryDisplayComponent;

  const mockItinerary: FinalItinerary = {
    id: 'plan-iceland-123',
    neighborhoods: {},
    cost_optimization_tips: [],
    review_status: 'approved',
    logistics_summary: 'Reykjavik → Golden Circle → Vík → Höfn → Akureyri',
    strategic_insight: 'Counter-clockwise Ring Road routing avoids tourist convoys.',
    constraints: {
      origin: 'NAG',
      destination_region: 'Iceland Ring Road',
      duration_days: 11,
      cities: ['Reykjavik', 'Vík', 'Höfn', 'Akureyri'],
      budget_total: 350000,
      currency: 'INR',
      preferences: [],
      avoidances: [],
      is_road_trip: true
    },
    days: [
      {
        day_number: 1,
        city: 'Reykjavik',
        day_summary: 'Arrival and exploration',
        day_narrative: 'Arrive at KEF, pick up 4WD vehicle.',
        day_cost: 15000,
        driving_time_to_next: '1.0 h to Golden Circle',
        items: [
          { slot_index: 0, time: '14:00', activity_name: 'Pick up 4x4 car at KEF', cost_estimate: 0, notes: 'N1 gas card' }
        ],
        places: [
          { id: 'pl-1', name: 'Sun Voyager', rating: 4.6, review_count: 5000, types: ['tourist_attraction'] }
        ],
        hotel_options: [
          {
            id: 'h-1',
            name: 'Hotel Reykjavik',
            city: 'Reykjavik',
            price_per_night: 180,
            currency: 'USD',
            guest_rating: 8.8,
            star_rating: 4,
            deeplink: 'https://booking.com/sample'
          }
        ]
      },
      {
        day_number: 2,
        city: 'Vík',
        day_summary: 'South Shore and waterfalls',
        day_narrative: 'Morning at Seljalandsfoss and black sand beaches.',
        day_cost: 18000,
        driving_time_to_next: '2.5 h to Höfn',
        items: [
          { slot_index: 0, time: '08:00', activity_name: 'Seljalandsfoss Waterfall', cost_estimate: 0 }
        ],
        places: [
          { id: 'pl-2', name: 'Reynisfjara Beach', rating: 4.8, review_count: 12000, types: ['natural_feature'] }
        ],
        hotel_options: [
          {
            id: 'h-2',
            name: 'Hotel Vík í Mýrdal',
            city: 'Vík',
            price_per_night: 220,
            currency: 'USD',
            guest_rating: 9.0,
            star_rating: 4
          }
        ]
      }
    ],
    budget_rollup: {
      grand_total: 312400,
      currency: 'INR',
      categories: [
        { category: 'stay', estimated_total: 118000, currency: 'INR', notes: 'Stays' },
        { category: 'transport', estimated_total: 82000, currency: 'INR', notes: 'Car rental' },
        { category: 'food', estimated_total: 45000, currency: 'INR', notes: 'Food & Fuel' },
        { category: 'activities', estimated_total: 32000, currency: 'INR', notes: 'Parks' }
      ]
    },
    flight_options: [
      {
        id: 'fl-1',
        airline: 'IndiGo + Lufthansa',
        flight_number: 'LH820',
        price: 74200,
        currency: 'INR',
        duration_minutes: 1050,
        stops: 2,
        layover_airports: ['DEL', 'FRA'],
        origin: 'NAG',
        destination: 'KEF',
        departure: '2026-10-01T06:00:00',
        arrival: '2026-10-01T23:30:00'
      }
    ],
    car_estimates: [
      {
        id: 'car-1',
        supplier: 'Skyscanner Cars',
        vehicle_name: 'Suzuki Vitara 4x4',
        category: 'SUV',
        price_per_day: 45,
        total_price: 495,
        currency: 'USD',
        seats: 5,
        transmission: 'Automatic',
        is_estimate: true
      }
    ],
    map_pins: [
      { id: 'pin-1', label: 'Reykjavik', lat: 64.146, lng: -21.942, day_number: 1, pin_type: 'overnight' },
      { id: 'pin-2', label: 'Vík', lat: 63.418, lng: -19.006, day_number: 2, pin_type: 'overnight' }
    ]
  };

  beforeEach(() => {
    component = new ItineraryDisplayComponent();
    component.itinerary = mockItinerary;
  });

  it('should instantiate and default to Day 1', () => {
    expect(component).toBeDefined();
    expect(component.activeDayNumber()).toBe(1);
    expect(component.activeDay.city).toBe('Reykjavik');
  });

  it('should switch active day when selectDay is called', () => {
    component.selectDay(2);
    expect(component.activeDayNumber()).toBe(2);
    expect(component.activeDay.city).toBe('Vík');
  });

  it('should compute contingency buffer correctly', () => {
    // 350000 - 312400 = 37600
    expect(component.getContingencyBuffer()).toBe(37600);
  });

  it('should compute average flight fare and daily drive average', () => {
    expect(component.getAverageFlightFare()).toBe(74200);
    expect(component.getDailyDriveAverage()).toBeDefined();
    expect(component.getPacingScore()).toBe('9.8 / 10');
  });

  it('should toggle map modal and remaining days table', () => {
    expect(component.showMapModal()).toBe(false);
    component.toggleMap();
    expect(component.showMapModal()).toBe(true);

    expect(component.showRemainingDaysTable()).toBe(false);
    component.toggleRemainingDays();
    expect(component.showRemainingDaysTable()).toBe(true);
  });

  it('should toggle smart swap applied state', () => {
    expect(component.appliedSwap()).toBe(false);
    component.applySmartSwap();
    expect(component.appliedSwap()).toBe(true);
  });

  it('should emit searchFlights event on flight selection', () => {
    const spy = vi.spyOn(component.searchFlights, 'emit');
    component.onSearchFlightsClick(mockItinerary.flight_options![0]);
    expect(spy).toHaveBeenCalledWith(mockItinerary.flight_options![0]);
  });

  describe('Phase 11 - Booking Integration URLs & Actions', () => {
    it('should return direct deeplink for hotel when present', () => {
      const hotelWithDeeplink = mockItinerary.days[0].hotel_options![0];
      const url = component.getHotelBookingUrl(hotelWithDeeplink, mockItinerary.days[0]);
      expect(url).toBe('https://booking.com/sample');
    });

    it('should generate fallback Booking.com search URL when deeplink is absent', () => {
      const hotelWithoutDeeplink = mockItinerary.days[1].hotel_options![0];
      const url = component.getHotelBookingUrl(hotelWithoutDeeplink, mockItinerary.days[1]);
      expect(url).toContain('https://www.booking.com/searchresults.html?ss=');
      expect(url).toContain(encodeURIComponent('Hotel Vík í Mýrdal, Vík'));
    });

    it('should return direct deeplink for car rental when present', () => {
      const carWithDeeplink = {
        ...mockItinerary.car_estimates![0],
        deeplink: 'https://www.skyscanner.net/carhire?pickup=KEF'
      };
      const url = component.getCarBookingUrl(carWithDeeplink);
      expect(url).toBe('https://www.skyscanner.net/carhire?pickup=KEF');
    });

    it('should generate fallback Skyscanner Car Hire URL when car deeplink is absent', () => {
      const url = component.getCarBookingUrl(mockItinerary.car_estimates![0]);
      expect(url).toContain('https://www.skyscanner.net/carhire?pickup=');
      expect(url).toContain('KEF');
    });

    it('should generate Google Maps driving directions route URL with waypoints', () => {
      const routeUrl = component.getGoogleMapsRouteUrl();
      expect(routeUrl).toContain('https://www.google.com/maps/dir/');
      expect(routeUrl).toContain('Reykjavik');
    });

    it('should return place google_maps_url or fallback search query', () => {
      const placeWithMaps = {
        id: 'p-1',
        name: 'Gullfoss',
        google_maps_url: 'https://maps.google.com/?cid=12345'
      };
      expect(component.getPlaceMapsUrl(placeWithMaps)).toBe('https://maps.google.com/?cid=12345');

      const placeWithoutMaps = {
        id: 'p-2',
        name: 'Geysir Geothermal Area',
        city: 'Haukadalur'
      };
      const fallbackUrl = component.getPlaceMapsUrl(placeWithoutMaps);
      expect(fallbackUrl).toContain('https://www.google.com/maps/search/?api=1&query=');
      expect(fallbackUrl).toContain(encodeURIComponent('Geysir Geothermal Area, Haukadalur'));
    });

    it('should emit bookStay event on stay booking click', () => {
      const spy = vi.spyOn(component.bookStay, 'emit');
      const hotel = mockItinerary.days[0].hotel_options![0];
      component.onBookStayClick(hotel, mockItinerary.days[0]);
      expect(spy).toHaveBeenCalledWith(hotel);
    });

    it('should emit bookCar event on car rental booking click', () => {
      const spy = vi.spyOn(component.bookCar, 'emit');
      const car = mockItinerary.car_estimates![0];
      component.onBookCarClick(car);
      expect(spy).toHaveBeenCalledWith(car);
    });

    it('should return 3 tier-calibrated hotel options per city (SF-3)', () => {
      const hotels = component.getActiveDayHotels();
      expect(hotels.length).toBe(3);
      expect(hotels[0].name).toBe('Hotel Reykjavik');
      expect(hotels[1].name).toContain('Reykjavik');
      expect(hotels[2].name).toContain('Reykjavik');
    });

    it('should return 2-3 verified places for active day (C-3)', () => {
      const places = component.getActiveDayPlaces();
      expect(places.length).toBeGreaterThanOrEqual(2);
      expect(places.length).toBeLessThanOrEqual(3);
      expect(places[0].name).toBe('Sun Voyager');
    });

    it('should emit refined prompt when refineItinerary is invoked (C-1)', () => {
      const spy = vi.spyOn(component.selectPrompt, 'emit');
      component.refineItinerary('budget');
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('tighter budget'));

      component.refineItinerary('swap_city');
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('swap one destination'));

      component.refineItinerary('deep_dive');
      expect(spy).toHaveBeenCalledWith(expect.stringContaining('extra deep dive'));
    });
  });
});
