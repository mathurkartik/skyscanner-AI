import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CurrencyService } from '../../services/currency.service';
import { HOTELS_DATA } from '../../data/travel.data';
import { HotelOffer } from '../../models/travel.model';

@Component({
  selector: 'app-hotel-search',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './hotel-search.component.html',
  styleUrls: ['./hotel-search.component.css']
})
export class HotelSearchComponent {
  public readonly currencyService = inject(CurrencyService);

  public destination = signal<string>('Tokyo, Japan');
  public checkIn = signal<string>('2026-11-15');
  public checkOut = signal<string>('2026-11-20');
  public guests = signal<number>(2);
  public minRating = signal<number>(0);
  public freeCancelOnly = signal<boolean>(false);
  public breakfastOnly = signal<boolean>(false);

  public bookedHotel = signal<HotelOffer | null>(null);

  public readonly filteredHotels = computed(() => {
    let list = HOTELS_DATA;
    if (this.freeCancelOnly()) {
      list = list.filter(h => h.freeCancellation);
    }
    if (this.breakfastOnly()) {
      list = list.filter(h => h.breakfastIncluded);
    }
    if (this.minRating() > 0) {
      list = list.filter(h => h.starRating >= this.minRating());
    }
    return list;
  });

  public book(hotel: HotelOffer) {
    this.bookedHotel.set(hotel);
  }

  public closeBooking() {
    this.bookedHotel.set(null);
  }
}
