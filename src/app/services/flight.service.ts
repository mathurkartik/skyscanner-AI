import { Injectable, signal, computed, inject } from '@angular/core';
import { FlightOffer, SearchQuery, FlightFilterState, SortOption, Airport } from '../models/flight.model';
import { POPULAR_AIRPORTS } from '../data/airports.data';
import { generateFlightsForRoute } from '../data/flights.data';
import { SkyscannerApiService } from './skyscanner-api.service';

@Injectable({
  providedIn: 'root'
})
export class FlightService {
  private readonly skyscannerApi = inject(SkyscannerApiService);

  // Navigation / View mode
  public readonly isResultsView = signal<boolean>(false);
  public readonly showApiSettingsModal = signal<boolean>(false);

  // Checkbox states from homepage
  public readonly addPlaceToStay = signal<boolean>(true);
  public readonly nearbyOrigin = signal<boolean>(false);
  public readonly nearbyDestination = signal<boolean>(false);

  // Default Search Query matching screenshot (From: Nagpur (NAG), Destination: Singapore or Tokyo)
  public readonly searchQuery = signal<SearchQuery>({
    tripType: 'round-trip',
    origin: POPULAR_AIRPORTS[0], // Nagpur (NAG)
    destination: POPULAR_AIRPORTS.find(a => a.code === 'SIN') || POPULAR_AIRPORTS[19], // Singapore (SIN)
    departDate: '2026-11-15',
    returnDate: '2026-11-22',
    adults: 1,
    children: 0,
    cabinClass: 'economy',
    directOnly: false
  });

  // Raw Flights
  private readonly rawFlights = signal<FlightOffer[]>([]);

  // Sorting
  public readonly sortOption = signal<SortOption>('best');

  // Filters
  public readonly filterState = signal<FlightFilterState>({
    stops: [0, 1, 2],
    airlines: [],
    maxPriceUSD: 3000,
    maxDurationMinutes: 2000,
    departureTimeRange: 'all',
    greenerChoiceOnly: false
  });

  // Active Selected Offer (for details modal)
  public readonly selectedOffer = signal<FlightOffer | null>(null);

  // Price Alert state
  public readonly priceAlertActive = signal<boolean>(false);

  // Loading state & Source tag
  public readonly isLoading = signal<boolean>(false);
  public readonly dataSource = signal<'live' | 'realistic'>('realistic');

  constructor() {
    this.executeSearch(this.searchQuery(), false);
  }

  public async executeSearch(query: SearchQuery, openResults = true) {
    this.isLoading.set(true);
    this.searchQuery.set(query);
    if (openResults) {
      this.isResultsView.set(true);
    }

    // Try live Skyscanner RapidAPI if Live Mode is enabled with a key
    if (this.skyscannerApi.isLiveMode() && this.skyscannerApi.apiKey()) {
      try {
        const liveOffers = await this.skyscannerApi.searchLiveFlights(
          query.origin,
          query.destination,
          query.departDate,
          query.tripType === 'round-trip' ? query.returnDate : null,
          query.cabinClass,
          query.adults + query.children
        );

        if (liveOffers.length > 0) {
          this.rawFlights.set(liveOffers);
          this.dataSource.set('live');
          this.isLoading.set(false);
          return;
        }
      } catch (err) {
        console.warn('Live Skyscanner API call failed, falling back to realistic hub-and-spoke generator:', err);
      }
    }

    // Fallback: Realistic Hub-and-Spoke route generator
    setTimeout(() => {
      let flights = generateFlightsForRoute(
        query.origin,
        query.destination,
        query.departDate,
        query.tripType === 'round-trip' ? query.returnDate : null,
        query.cabinClass,
        query.adults + query.children
      );

      if (query.directOnly) {
        flights = flights.filter(f => f.outbound.stopsCount === 0);
      }

      this.rawFlights.set(flights);
      this.dataSource.set('realistic');
      this.isLoading.set(false);
    }, 300);
  }

  public goToHomepage() {
    this.isResultsView.set(false);
  }

  public openApiSettings() {
    this.showApiSettingsModal.set(true);
  }

  public closeApiSettings() {
    this.showApiSettingsModal.set(false);
  }

  // Filtered & Sorted Flights
  public readonly filteredFlights = computed(() => {
    const raw = this.rawFlights();
    const filters = this.filterState();
    const sort = this.sortOption();

    let result = raw.filter(offer => {
      // Stops filter
      if (!filters.stops.includes(offer.outbound.stopsCount)) {
        return false;
      }

      // Airlines filter
      if (filters.airlines.length > 0 && !filters.airlines.includes(offer.outbound.airline)) {
        return false;
      }

      // Max price
      if (offer.priceUSD > filters.maxPriceUSD) {
        return false;
      }

      // Max duration
      if (offer.outbound.durationMinutes > filters.maxDurationMinutes) {
        return false;
      }

      // Greener choice only
      if (filters.greenerChoiceOnly && !offer.co2ReductionPercent) {
        return false;
      }

      // Departure time range
      if (filters.departureTimeRange !== 'all') {
        const hour = parseInt(offer.outbound.departureTime.split(':')[0], 10);
        if (filters.departureTimeRange === 'morning' && (hour < 5 || hour >= 12)) return false;
        if (filters.departureTimeRange === 'afternoon' && (hour < 12 || hour >= 18)) return false;
        if (filters.departureTimeRange === 'evening' && (hour < 18 && hour >= 5)) return false;
      }

      return true;
    });

    // Sorting
    if (sort === 'cheapest') {
      result.sort((a, b) => a.priceUSD - b.priceUSD);
    } else if (sort === 'fastest') {
      result.sort((a, b) => a.outbound.durationMinutes - b.outbound.durationMinutes);
    } else {
      // Best
      result.sort((a, b) => {
        if (a.best && !b.best) return -1;
        if (!a.best && b.best) return 1;
        return a.priceUSD - b.priceUSD;
      });
    }

    return result;
  });

  // Metrics for Filter Sidebar
  public readonly availableAirlines = computed(() => {
    const flights = this.rawFlights();
    const airlineMap = new Map<string, number>();
    flights.forEach(f => {
      const currentMin = airlineMap.get(f.outbound.airline);
      if (!currentMin || f.priceUSD < currentMin) {
        airlineMap.set(f.outbound.airline, f.priceUSD);
      }
    });
    return Array.from(airlineMap.entries()).map(([name, minPrice]) => ({ name, minPrice }));
  });

  public readonly stopsSummary = computed(() => {
    const flights = this.rawFlights();
    const getMin = (stops: number) => {
      const matching = flights.filter(f => f.outbound.stopsCount === stops);
      if (matching.length === 0) return null;
      return Math.min(...matching.map(f => f.priceUSD));
    };
    return {
      direct: getMin(0),
      oneStop: getMin(1),
      twoPlus: getMin(2)
    };
  });

  public setSort(sort: SortOption) {
    this.sortOption.set(sort);
  }

  public updateFilter(partial: Partial<FlightFilterState>) {
    this.filterState.update(prev => ({ ...prev, ...partial }));
  }

  public resetFilters() {
    this.filterState.set({
      stops: [0, 1, 2],
      airlines: [],
      maxPriceUSD: 3000,
      maxDurationMinutes: 2000,
      departureTimeRange: 'all',
      greenerChoiceOnly: false
    });
  }

  public openFlightDetails(offer: FlightOffer) {
    this.selectedOffer.set(offer);
  }

  public closeFlightDetails() {
    this.selectedOffer.set(null);
  }

  public togglePriceAlert() {
    this.priceAlertActive.update(val => !val);
  }
}
