import { Component, inject, signal, computed, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FlightService } from '../../services/flight.service';
import { Airport, TripType, CabinClass, SearchQuery } from '../../models/flight.model';
import { POPULAR_AIRPORTS } from '../../data/airports.data';

@Component({
  selector: 'app-flight-search',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './flight-search.component.html',
  styleUrls: ['./flight-search.component.css']
})
export class FlightSearchComponent {
  public readonly flightService = inject(FlightService);
  public readonly exploreRequested = output<void>();

  public readonly airports = POPULAR_AIRPORTS;

  // Form State (Defaulting to Nagpur NAG as in the screenshot)
  public tripType = signal<TripType>('round-trip');
  public origin = signal<Airport>(POPULAR_AIRPORTS[0]); // Nagpur (NAG)
  public destination = signal<Airport | null>(null); // Country, city or airport
  public departDate = signal<string>('2026-11-15');
  public returnDate = signal<string>('2026-11-22');
  public adults = signal<number>(1);
  public children = signal<number>(0);
  public cabinClass = signal<CabinClass>('economy');
  public directOnly = signal<boolean>(false);
  public nearbyOrigin = signal<boolean>(false);
  public nearbyDestination = signal<boolean>(false);
  public addPlaceToStay = signal<boolean>(true);
  public bagsCount = signal<number>(1);

  // Dropdowns
  public isTripTypeDropdownOpen = signal<boolean>(false);
  public isBagsDropdownOpen = signal<boolean>(false);
  public isOriginOpen = signal<boolean>(false);
  public isDestinationOpen = signal<boolean>(false);
  public isDepartDateOpen = signal<boolean>(false);
  public isReturnDateOpen = signal<boolean>(false);
  public isPassengersOpen = signal<boolean>(false);

  public originSearch = signal<string>('');
  public destinationSearch = signal<string>('');

  private normalizeStr(str: string): string {
    return str.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();
  }

  public filteredOriginAirports = computed(() => {
    const raw = this.originSearch();
    if (!raw.trim()) return this.airports;
    const q = this.normalizeStr(raw);
    return this.airports.filter(a => 
      this.normalizeStr(a.city).includes(q) || 
      this.normalizeStr(a.code).includes(q) || 
      this.normalizeStr(a.name).includes(q) ||
      (a.country ? this.normalizeStr(a.country).includes(q) : false)
    );
  });

  public filteredDestinationAirports = computed(() => {
    const raw = this.destinationSearch();
    if (!raw.trim()) return this.airports;
    const q = this.normalizeStr(raw);
    return this.airports.filter(a => 
      this.normalizeStr(a.city).includes(q) || 
      this.normalizeStr(a.code).includes(q) || 
      this.normalizeStr(a.name).includes(q) ||
      (a.country ? this.normalizeStr(a.country).includes(q) : false)
    );
  });

  public totalPassengers = computed(() => this.adults() + this.children());

  public tripTypeLabel = computed(() => {
    switch (this.tripType()) {
      case 'round-trip': return 'Return';
      case 'one-way': return 'One way';
      case 'multi-city': return 'Multi-city';
    }
  });

  public cabinClassLabel = computed(() => {
    switch (this.cabinClass()) {
      case 'economy': return 'Economy';
      case 'premium_economy': return 'Premium Economy';
      case 'business': return 'Business Class';
      case 'first': return 'First Class';
    }
  });

  public setTripType(type: TripType) {
    this.tripType.set(type);
    this.isTripTypeDropdownOpen.set(false);
  }

  public swapAirports(event: MouseEvent) {
    event.stopPropagation();
    if (this.destination()) {
      const temp = this.origin();
      this.origin.set(this.destination()!);
      this.destination.set(temp);
    }
  }

  public selectOrigin(airport: Airport) {
    this.origin.set(airport);
    this.isOriginOpen.set(false);
    this.originSearch.set('');
  }

  public selectDestination(airport: Airport) {
    this.destination.set(airport);
    this.isDestinationOpen.set(false);
    this.destinationSearch.set('');
  }

  public triggerExploreEverywhere() {
    this.isDestinationOpen.set(false);
    this.exploreRequested.emit();
  }

  public incrementAdults() {
    if (this.adults() < 9) this.adults.update(v => v + 1);
  }

  public decrementAdults() {
    if (this.adults() > 1) this.adults.update(v => v - 1);
  }

  public incrementChildren() {
    if (this.children() < 8) this.children.update(v => v + 1);
  }

  public decrementChildren() {
    if (this.children() > 0) this.children.update(v => v - 1);
  }

  public onSearch() {
    // If no destination picked, default to Tokyo or first global hub
    const dest = this.destination() || this.airports.find(a => a.code === 'HND') || this.airports[6];

    const query: SearchQuery = {
      tripType: this.tripType(),
      origin: this.origin(),
      destination: dest,
      departDate: this.departDate(),
      returnDate: this.returnDate(),
      adults: this.adults(),
      children: this.children(),
      cabinClass: this.cabinClass(),
      directOnly: this.directOnly()
    };
    
    this.flightService.executeSearch(query, true);
  }
}
