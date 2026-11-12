import { Injectable, signal } from '@angular/core';

// SSR-safe storage helper (AG-023)
function getStoredFavorites(): string[] {
  if (typeof localStorage !== 'undefined') {
    try {
      return JSON.parse(localStorage.getItem('skyscanner_saved_flights') || '[]');
    } catch {
      return [];
    }
  }
  return [];
}

@Injectable({
  providedIn: 'root'
})
export class FavoritesService {
  private savedFlightIds = signal<string[]>(getStoredFavorites());

  public readonly savedList = this.savedFlightIds.asReadonly();

  public isFlightSaved(id: string): boolean {
    return this.savedFlightIds().includes(id);
  }

  public toggleFlight(id: string) {
    this.savedFlightIds.update(current => {
      let updated: string[];
      if (current.includes(id)) {
        updated = current.filter(x => x !== id);
      } else {
        updated = [...current, id];
      }
      if (typeof localStorage !== 'undefined') {
        try {
          localStorage.setItem('skyscanner_saved_flights', JSON.stringify(updated));
        } catch {}
      }
      return updated;
    });
  }
}

