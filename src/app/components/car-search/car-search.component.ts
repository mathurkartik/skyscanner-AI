import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CurrencyService } from '../../services/currency.service';
import { CARS_DATA } from '../../data/travel.data';
import { CarOffer } from '../../models/travel.model';

@Component({
  selector: 'app-car-search',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './car-search.component.html',
  styleUrls: ['./car-search.component.css']
})
export class CarSearchComponent {
  public readonly currencyService = inject(CurrencyService);

  public location = signal<string>('Tokyo Haneda Airport (HND)');
  public pickupDate = signal<string>('2026-11-15');
  public dropoffDate = signal<string>('2026-11-20');
  public categoryFilter = signal<string>('All');
  public bookedCar = signal<CarOffer | null>(null);

  public readonly filteredCars = computed(() => {
    if (this.categoryFilter() === 'All') return CARS_DATA;
    return CARS_DATA.filter(c => c.category === this.categoryFilter());
  });

  public setCategory(cat: string) {
    this.categoryFilter.set(cat);
  }

  public book(car: CarOffer) {
    this.bookedCar.set(car);
  }

  public closeBooking() {
    this.bookedCar.set(null);
  }
}
