import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createEnvironmentInjector, runInInjectionContext } from '@angular/core';
import { FlightSearchComponent } from './flight-search.component';
import { FlightService } from '../../services/flight.service';
import { SkyscannerApiService } from '../../services/skyscanner-api.service';
import { CurrencyService } from '../../services/currency.service';

if (typeof localStorage === 'undefined') {
  let store: Record<string, string> = {};
  (globalThis as any).localStorage = {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; }
  };
}

describe('FlightSearchComponent (AG-116)', () => {
  let component: FlightSearchComponent;
  let injector: any;

  beforeEach(() => {
    injector = createEnvironmentInjector([
      CurrencyService,
      SkyscannerApiService,
      FlightService,
    ], null as any);

    component = runInInjectionContext(injector, () => new FlightSearchComponent());
  });

  it('initializes with default search parameters', () => {
    expect(component.tripType()).toBe('round-trip');
    expect(component.adults()).toBe(1);
    expect(component.cabinClass()).toBe('economy');
    expect(component.origin()).toBeDefined();
  });

  it('filters origin airports by query', () => {
    component.originSearch.set('London');
    const filtered = component.filteredOriginAirports();
    expect(filtered.length).toBeGreaterThan(0);
    expect(filtered.some(a => a.city.toLowerCase().includes('london'))).toBe(true);
  });

  it('swaps origin and destination', () => {
    const orig = component.origin();
    const dest = component.airports[1];
    component.destination.set(dest);

    const mockEvent = { stopPropagation: vi.fn() } as unknown as MouseEvent;
    component.swapAirports(mockEvent);

    expect(component.origin()?.code).toBe(dest.code);
    expect(component.destination()?.code).toBe(orig?.code);
  });

  it('updates passenger counts within bounds', () => {
    component.incrementAdults();
    expect(component.adults()).toBe(2);

    component.decrementAdults();
    expect(component.adults()).toBe(1);

    // Cannot go below 1 adult
    component.decrementAdults();
    expect(component.adults()).toBe(1);
  });

  it('triggers search on flightService when onSearch is called', () => {
    const searchSpy = vi.spyOn(component.flightService, 'executeSearch');
    component.destination.set(component.airports[1]);
    component.onSearch();
    expect(searchSpy).toHaveBeenCalled();
  });
});
