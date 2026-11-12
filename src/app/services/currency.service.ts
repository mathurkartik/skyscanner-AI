import { Injectable, signal, computed } from '@angular/core';

export interface Currency {
  code: string;
  symbol: string;
  name: string;
  rateAgainstUSD: number;
}

export const SUPPORTED_CURRENCIES: Currency[] = [
  { code: 'USD', symbol: '$', name: 'US Dollar', rateAgainstUSD: 1 },
  { code: 'EUR', symbol: '€', name: 'Euro', rateAgainstUSD: 0.92 },
  { code: 'GBP', symbol: '£', name: 'British Pound', rateAgainstUSD: 0.79 },
  { code: 'JPY', symbol: '¥', name: 'Japanese Yen', rateAgainstUSD: 153.5 },
  { code: 'INR', symbol: '₹', name: 'Indian Rupee', rateAgainstUSD: 85.2 },
  { code: 'CAD', symbol: 'CA$', name: 'Canadian Dollar', rateAgainstUSD: 1.39 },
  { code: 'AUD', symbol: 'A$', name: 'Australian Dollar', rateAgainstUSD: 1.54 },
];

// SSR-safe storage helper (AG-023)
function getStoredCurrency(): string {
  if (typeof localStorage !== 'undefined') {
    try {
      return localStorage.getItem('skyscanner_currency') || 'USD';
    } catch {
      return 'USD';
    }
  }
  return 'USD';
}

@Injectable({
  providedIn: 'root'
})
export class CurrencyService {
  private currentCurrencyCode = signal<string>(getStoredCurrency());

  public readonly currencies = SUPPORTED_CURRENCIES;

  public readonly selectedCurrency = computed(() => {
    const code = this.currentCurrencyCode();
    return this.currencies.find(c => c.code === code) || this.currencies[0];
  });

  public setCurrency(code: string) {
    const found = this.currencies.find(c => c.code === code);
    if (found) {
      this.currentCurrencyCode.set(code);
      if (typeof localStorage !== 'undefined') {
        try {
          localStorage.setItem('skyscanner_currency', code);
        } catch {}
      }
    }
  }

  public convert(amountUSD: number): number {
    const curr = this.selectedCurrency();
    return Math.round(amountUSD * curr.rateAgainstUSD);
  }

  public format(amountUSD: number): string {
    const curr = this.selectedCurrency();
    const converted = this.convert(amountUSD);
    return `${curr.symbol}${converted.toLocaleString()}`;
  }
}

