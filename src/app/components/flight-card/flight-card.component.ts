import { Component, inject, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FlightOffer } from '../../models/flight.model';
import { CurrencyService } from '../../services/currency.service';
import { FavoritesService } from '../../services/favorites.service';

@Component({
  selector: 'app-flight-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './flight-card.component.html',
  styleUrls: ['./flight-card.component.css']
})
export class FlightCardComponent {
  public readonly flight = input.required<FlightOffer>();
  public readonly currencyService = inject(CurrencyService);
  public readonly favoritesService = inject(FavoritesService);

  public readonly selectFlight = output<FlightOffer>();

  public formatDuration(minutes: number): string {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins > 0 ? mins + 'm' : ''}`;
  }

  public onSelect() {
    this.selectFlight.emit(this.flight());
  }

  public toggleFavorite(event: MouseEvent) {
    event.stopPropagation();
    this.favoritesService.toggleFlight(this.flight().id);
  }

  public isSaved(): boolean {
    return this.favoritesService.isFlightSaved(this.flight().id);
  }
}
