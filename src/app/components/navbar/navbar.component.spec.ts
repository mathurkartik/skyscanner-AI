import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createEnvironmentInjector, runInInjectionContext } from '@angular/core';
import { NavbarComponent, MainTab } from './navbar.component';
import { CurrencyService } from '../../services/currency.service';
import { FavoritesService } from '../../services/favorites.service';
import { FlightService } from '../../services/flight.service';
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

describe('NavbarComponent (AG-116)', () => {
  let component: NavbarComponent;
  let injector: any;

  beforeEach(() => {
    injector = createEnvironmentInjector([
      CurrencyService,
      FavoritesService,
      FlightService,
      SkyscannerApiService,
    ], null as any);

    component = runInInjectionContext(injector, () => new NavbarComponent());
  });

  it('initializes with default modal and login signals', () => {
    expect(component.isLocaleModalOpen()).toBe(false);
    expect(component.isLoginModalOpen()).toBe(false);
    expect(component.isHelpModalOpen()).toBe(false);
    expect(component.isFavoritesOpen()).toBe(false);
    expect(component.isLoggedIn()).toBe(false);
  });

  it('toggles locale modal open and close', () => {
    component.toggleLocaleModal();
    expect(component.isLocaleModalOpen()).toBe(true);

    component.toggleLocaleModal();
    expect(component.isLocaleModalOpen()).toBe(false);
  });

  it('toggles favorites modal', () => {
    component.toggleFavorites();
    expect(component.isFavoritesOpen()).toBe(true);

    component.toggleFavorites();
    expect(component.isFavoritesOpen()).toBe(false);
  });

  it('handles user login and logout', () => {
    component.handleLogin();
    expect(component.isLoggedIn()).toBe(true);
    expect(component.isLoginModalOpen()).toBe(false);

    component.handleLogout();
    expect(component.isLoggedIn()).toBe(false);
  });

  it('emits tabChanged when setTab is called', () => {
    const emitSpy = vi.spyOn(component.tabChanged, 'emit');
    component.setTab('flights');
    expect(emitSpy).toHaveBeenCalledWith('flights');

    component.setTab('ai');
    expect(emitSpy).toHaveBeenCalledWith('ai');
  });
});
