import { Component, inject, signal, computed, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CurrencyService } from '../../services/currency.service';
import { FlightService } from '../../services/flight.service';
import { EXPLORE_DESTINATIONS } from '../../data/travel.data';
import { ExploreDestination } from '../../models/travel.model';
import { POPULAR_AIRPORTS } from '../../data/airports.data';

@Component({
  selector: 'app-explore-everywhere',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './explore-everywhere.component.html',
  styleUrls: ['./explore-everywhere.component.css']
})
export class ExploreEverywhereComponent {
  public readonly currencyService = inject(CurrencyService);
  public readonly flightService = inject(FlightService);

  public readonly destinationChosen = output<void>();

  public maxBudgetUSD = signal<number>(1000);
  public flightTypeFilter = signal<'All' | 'Direct'>('All');

  public readonly destinations = computed(() => {
    let list = EXPLORE_DESTINATIONS.filter(d => d.priceFromUSD <= this.maxBudgetUSD());
    if (this.flightTypeFilter() === 'Direct') {
      list = list.filter(d => d.flightType === 'Direct');
    }
    return list;
  });

  public selectDestination(item: ExploreDestination) {
    const airport = POPULAR_AIRPORTS.find(a => a.code === item.airportCode) || {
      code: item.airportCode,
      name: `${item.city} International`,
      city: item.city,
      country: item.country
    };

    const currentQuery = this.flightService.searchQuery();
    this.flightService.executeSearch({
      ...currentQuery,
      destination: airport
    });

    this.destinationChosen.emit();
  }
}
