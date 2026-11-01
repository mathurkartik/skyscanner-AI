import { Injectable, signal } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class FavoritesService {
  private savedFlightIds = signal<string[]>(
    JSON.parse(localStorage.getItem('skyscanner_saved_flights') || '[]')
  );

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
      localStorage.setItem('skyscanner_saved_flights', JSON.stringify(updated));
      return updated;
    });
  }
}

