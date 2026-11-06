import '@angular/compiler';
import { describe, it, expect, beforeEach } from 'vitest';
import { createEnvironmentInjector } from '@angular/core';
import { App } from './app';
import { FlightService } from './services/flight.service';
import { CurrencyService } from './services/currency.service';
import { SkyscannerApiService } from './services/skyscanner-api.service';

if (typeof localStorage === 'undefined') {
  let store: Record<string, string> = {};
  (globalThis as any).localStorage = {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; }
  };
}

describe('Skyscanner App Component', () => {
  let injector: any;

  beforeEach(() => {
    injector = createEnvironmentInjector([SkyscannerApiService, FlightService, CurrencyService], null as any);
  });

  it('should instantiate App component with default AI travel planner tab', () => {
    const app = injector.runInContext(() => new App());
    expect(app).toBeDefined();
    expect(app.currentTab()).toBe('ai');
  });

  it('should switch tabs between flights, hotels, cars, and explore', () => {
    const app = injector.runInContext(() => new App());
    app.onTabChange('hotels');
    expect(app.currentTab()).toBe('hotels');

    app.onTabChange('cars');
    expect(app.currentTab()).toBe('cars');

    app.onTabChange('explore');
    expect(app.currentTab()).toBe('explore');

    app.onTabChange('ai');
    expect(app.currentTab()).toBe('ai');

    // Switching from AI Planner back to flights
    app.onTabChange('flights');
    expect(app.currentTab()).toBe('flights');
  });
});
