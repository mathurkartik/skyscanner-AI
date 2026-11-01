import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FlightService } from '../../services/flight.service';
import { CurrencyService } from '../../services/currency.service';
import { SortOption, FlightOffer } from '../../models/flight.model';
import { FlightCardComponent } from '../flight-card/flight-card.component';
import { FlightFiltersComponent } from '../flight-filters/flight-filters.component';
import { FlightDetailsModalComponent } from '../flight-details-modal/flight-details-modal.component';

@Component({
  selector: 'app-flight-results',
  standalone: true,
  imports: [
    CommonModule,
    FlightCardComponent,
    FlightFiltersComponent,
    FlightDetailsModalComponent
  ],
  templateUrl: './flight-results.component.html',
  styleUrls: ['./flight-results.component.css']
})
export class FlightResultsComponent {
  public readonly flightService = inject(FlightService);
  public readonly currencyService = inject(CurrencyService);

  public readonly toastMessage = signal<string | null>(null);

  // Sorting metrics
  public readonly sortMetrics = computed(() => {
    const flights = this.flightService.filteredFlights();
    if (flights.length === 0) return null;

    const cheapestFlight = [...flights].sort((a, b) => a.priceUSD - b.priceUSD)[0];
    const fastestFlight = [...flights].sort((a, b) => a.outbound.durationMinutes - b.outbound.durationMinutes)[0];
    const bestFlight = flights.find(f => f.best) || flights[0];

    return {
      cheapest: {
        price: cheapestFlight.priceUSD,
        duration: cheapestFlight.outbound.durationMinutes
      },
      fastest: {
        price: fastestFlight.priceUSD,
        duration: fastestFlight.outbound.durationMinutes
      },
      best: {
        price: bestFlight.priceUSD,
        duration: bestFlight.outbound.durationMinutes
      }
    };
  });

  public setSort(sort: SortOption) {
    this.flightService.setSort(sort);
  }

  public handleSelectFlight(offer: FlightOffer) {
    this.flightService.openFlightDetails(offer);
  }

  public togglePriceAlert() {
    this.flightService.togglePriceAlert();
    if (this.flightService.priceAlertActive()) {
      this.showToast('Price Alert activated! We will notify you when fares drop for this route.');
    } else {
      this.showToast('Price Alert turned off.');
    }
  }

  public formatDuration(minutes: number): string {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins > 0 ? mins + 'm' : ''}`;
  }

  private showToast(msg: string) {
    this.toastMessage.set(msg);
    setTimeout(() => {
      this.toastMessage.set(null);
    }, 3500);
  }
}
