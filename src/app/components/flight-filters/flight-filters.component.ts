import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FlightService } from '../../services/flight.service';
import { CurrencyService } from '../../services/currency.service';

@Component({
  selector: 'app-flight-filters',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './flight-filters.component.html',
  styleUrls: ['./flight-filters.component.css']
})
export class FlightFiltersComponent {
  public readonly flightService = inject(FlightService);
  public readonly currencyService = inject(CurrencyService);

  public isStopSelected(stopsCount: number): boolean {
    return this.flightService.filterState().stops.includes(stopsCount);
  }

  public toggleStop(stopsCount: number) {
    const current = [...this.flightService.filterState().stops];
    const index = current.indexOf(stopsCount);
    if (index > -1) {
      if (current.length > 1) {
        current.splice(index, 1);
      }
    } else {
      current.push(stopsCount);
    }
    this.flightService.updateFilter({ stops: current });
  }

  public isAirlineSelected(airlineName: string): boolean {
    const airlines = this.flightService.filterState().airlines;
    return airlines.length === 0 || airlines.includes(airlineName);
  }

  public toggleAirline(airlineName: string) {
    let current = [...this.flightService.filterState().airlines];
    if (current.includes(airlineName)) {
      current = current.filter(a => a !== airlineName);
    } else {
      current.push(airlineName);
    }
    this.flightService.updateFilter({ airlines: current });
  }

  public setDepartureTimeRange(range: 'all' | 'morning' | 'afternoon' | 'evening') {
    this.flightService.updateFilter({ departureTimeRange: range });
  }

  public toggleGreenerChoice() {
    const current = this.flightService.filterState().greenerChoiceOnly;
    this.flightService.updateFilter({ greenerChoiceOnly: !current });
  }

  public resetAll() {
    this.flightService.resetFilters();
  }
}
