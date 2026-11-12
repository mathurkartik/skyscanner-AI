import '@angular/compiler';
import { describe, it, expect, beforeEach } from 'vitest';
import { createEnvironmentInjector, runInInjectionContext } from '@angular/core';
import { FooterComponent } from './footer.component';
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

describe('FooterComponent (AG-116)', () => {
  let component: FooterComponent;
  let injector: any;

  beforeEach(() => {
    injector = createEnvironmentInjector([
      CurrencyService,
    ], null as any);

    component = runInInjectionContext(injector, () => new FooterComponent());
  });

  it('initializes with current year dynamically (AG-103)', () => {
    const currentYear = new Date().getFullYear();
    expect(component.currentYear).toBe(currentYear);
  });

  it('toggles accordion sections (AG-112)', () => {
    expect(component.isExpanded('explore')).toBe(false);

    component.toggleSection('explore');
    expect(component.isExpanded('explore')).toBe(true);

    component.toggleSection('explore');
    expect(component.isExpanded('explore')).toBe(false);
  });
});

