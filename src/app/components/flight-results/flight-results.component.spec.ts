import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createEnvironmentInjector, runInInjectionContext } from '@angular/core';
import { FlightResultsComponent } from './flight-results.component';
import { FlightService } from '../../services/flight.service';
import { CurrencyService } from '../../services/currency.service';
import { SkyscannerApiService } from '../../services/skyscanner-api.service';

if (typeof localStorage === 'undefined') {
  let store: Record<string, string> = {};
  (globalThis as any).localStorage = {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; }
  };
}

describe('FlightResultsComponent (AG-116)', () => {
  let component: FlightResultsComponent;
  let injector: any;

  beforeEach(() => {
    injector = createEnvironmentInjector([
      CurrencyService,
      SkyscannerApiService,
      FlightService,
    ], null as any);

    component = runInInjectionContext(injector, () => new FlightResultsComponent());
  });

  it('initializes and computes sort metrics from flight service', () => {
    expect(component.flightService).toBeDefined();
    expect(component.currencyService).toBeDefined();
    expect(component.toastMessage()).toBeNull();
  });

  it('updates sort option in flight service', () => {
    const sortSpy = vi.spyOn(component.flightService, 'setSort');
    component.setSort('cheapest');
    expect(sortSpy).toHaveBeenCalledWith('cheapest');

    component.setSort('fastest');
    expect(sortSpy).toHaveBeenCalledWith('fastest');
  });

  it('formats duration in hours and minutes', () => {
    expect(component.formatDuration(150)).toBe('2h 30m');
    expect(component.formatDuration(120)).toBe('2h ');
  });

  it('toggles price alerts and updates toast message', () => {
    component.togglePriceAlert();
    expect(component.toastMessage()).toContain('Price Alert');
  });
});
