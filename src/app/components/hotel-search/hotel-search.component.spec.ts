import '@angular/compiler';
import { describe, it, expect, beforeEach } from 'vitest';
import { createEnvironmentInjector, runInInjectionContext } from '@angular/core';
import { HotelSearchComponent } from './hotel-search.component';
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

describe('HotelSearchComponent (AG-116)', () => {
  let component: HotelSearchComponent;
  let injector: any;

  beforeEach(() => {
    injector = createEnvironmentInjector([
      CurrencyService,
    ], null as any);

    component = runInInjectionContext(injector, () => new HotelSearchComponent());
  });

  it('initializes with default hotel search criteria', () => {
    expect(component.destination()).toBe('Tokyo, Japan');
    expect(component.guests()).toBe(2);
    expect(component.freeCancelOnly()).toBe(false);
    expect(component.breakfastOnly()).toBe(false);
  });

  it('filters hotels by free cancellation', () => {
    component.freeCancelOnly.set(true);
    const hotels = component.filteredHotels();
    expect(hotels.every(h => h.freeCancellation)).toBe(true);
  });

  it('filters hotels by breakfast inclusion', () => {
    component.breakfastOnly.set(true);
    const hotels = component.filteredHotels();
    expect(hotels.every(h => h.breakfastIncluded)).toBe(true);
  });

  it('sets booked hotel on book() and clears on closeBooking()', () => {
    const hotels = component.filteredHotels();
    expect(hotels.length).toBeGreaterThan(0);

    component.book(hotels[0]);
    expect(component.bookedHotel()).toBe(hotels[0]);

    component.closeBooking();
    expect(component.bookedHotel()).toBeNull();
  });
});

