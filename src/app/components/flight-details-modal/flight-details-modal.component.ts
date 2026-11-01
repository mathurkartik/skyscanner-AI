import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FlightService } from '../../services/flight.service';
import { CurrencyService } from '../../services/currency.service';
import { BookingProvider, FlightOffer } from '../../models/flight.model';

@Component({
  selector: 'app-flight-details-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './flight-details-modal.component.html',
  styleUrls: ['./flight-details-modal.component.css']
})
export class FlightDetailsModalComponent {
  public readonly flightService = inject(FlightService);
  public readonly currencyService = inject(CurrencyService);

  public readonly bookedProvider = signal<BookingProvider | null>(null);
  public readonly bookingConfirmed = signal<boolean>(false);

  public close() {
    this.flightService.closeFlightDetails();
    this.bookingConfirmed.set(false);
    this.bookedProvider.set(null);
  }

  public book(provider: BookingProvider) {
    this.bookedProvider.set(provider);
    this.bookingConfirmed.set(true);
  }

  public formatDuration(minutes: number): string {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins > 0 ? mins + 'm' : ''}`;
  }
}
