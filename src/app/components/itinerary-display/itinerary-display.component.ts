import { Component, Input, Output, EventEmitter, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FinalItinerary, DayItinerary, RealFlightOffer, RealHotelOffer, CarEstimate, PlaceInfo, CostSavingTip } from '../../models/travel-planner.model';

@Component({
  selector: 'app-itinerary-display',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './itinerary-display.component.html',
  styleUrls: ['./itinerary-display.component.css']
})
export class ItineraryDisplayComponent {
  @Input({ required: true }) public itinerary!: FinalItinerary;

  @Output() public searchFlights = new EventEmitter<RealFlightOffer>();
  @Output() public selectPrompt = new EventEmitter<string>();
  @Output() public bookStay = new EventEmitter<RealHotelOffer>();
  @Output() public bookCar = new EventEmitter<CarEstimate>();

  // Active day selection for the right-column deep dive
  public readonly activeDayNumber = signal<number>(1);

  // Modal / drawer state toggles
  public readonly showMapModal = signal<boolean>(false);
  public readonly showRemainingDaysTable = signal<boolean>(false);
  public readonly appliedSwap = signal<boolean>(false);

  // Active Day computation
  public get activeDay(): DayItinerary {
    if (!this.itinerary?.days || this.itinerary.days.length === 0) {
      return {
        day_number: 1,
        city: this.itinerary?.constraints?.destination_region || this.itinerary?.constraints?.cities?.[0] || 'Reykjavik',
        day_summary: 'Arrival and exploration',
        day_narrative: '',
        day_cost: 0,
        items: [],
        places: [],
        hotel_options: []
      };
    }
    const found = this.itinerary.days.find(d => d.day_number === this.activeDayNumber());
    return found || this.itinerary.days[0];
  }

  public selectDay(dayNumber?: number | null): void {
    if (dayNumber !== undefined && dayNumber !== null) {
      this.activeDayNumber.set(dayNumber);
    }
  }

  public getContingencyBuffer(): number {
    const budgetTotal = this.itinerary?.constraints?.budget_total || 350000;
    const grandTotal = this.itinerary?.budget_rollup?.grand_total || 312400;
    const diff = budgetTotal - grandTotal;
    return diff > 0 ? diff : Math.max(25000, Math.round(budgetTotal * 0.1));
  }

  public getOriginIata(): string {
    return this.itinerary?.flight_options?.[0]?.origin || this.itinerary?.constraints?.origin_city?.slice(0, 3)?.toUpperCase() || this.itinerary?.constraints?.origin || 'ORIG';
  }

  public getDestinationIata(): string {
    if (this.itinerary?.flight_options?.[0]?.destination) {
      return this.itinerary.flight_options[0].destination;
    }
    const dest = (this.itinerary?.constraints?.destination_region || '').toLowerCase();
    if (dest.includes('france') || dest.includes('paris')) return 'CDG';
    if (dest.includes('japan') || dest.includes('tokyo')) return 'HND';
    if (dest.includes('swiss') || dest.includes('zurich')) return 'ZRH';
    if (dest.includes('italy') || dest.includes('rome')) return 'FCO';
    if (dest.includes('russia') || dest.includes('moscow')) return 'SVO';
    if (dest.includes('australia') || dest.includes('melbourne')) return 'MEL';
    if (dest.includes('iceland') || dest.includes('reykjavik')) return 'KEF';
    return this.itinerary?.constraints?.cities?.[0]?.slice(0, 3)?.toUpperCase() || 'DEST';
  }

  public getAverageFlightFare(): number {
    if (this.itinerary?.flight_options && this.itinerary.flight_options.length > 0) {
      const sum = this.itinerary.flight_options.reduce((acc, f) => acc + (f.price || 0), 0);
      return Math.round(sum / this.itinerary.flight_options.length);
    }
    return 74200;
  }

  public getDailyDriveAverage(): string {
    if (!this.itinerary?.days || this.itinerary.days.length === 0) return '2.4';
    let count = 0;
    let totalHours = 0;
    for (const d of this.itinerary.days) {
      if (d.driving_time_to_next) {
        const match = d.driving_time_to_next.match(/([0-9.]+)\s*h/);
        if (match) {
          totalHours += parseFloat(match[1]);
          count++;
        }
      }
    }
    if (count > 0) {
      return (totalHours / this.itinerary.days.length).toFixed(1);
    }
    return '2.4';
  }

  public getPacingScore(): string {
    const days = this.itinerary?.constraints?.duration_days || 11;
    if (days >= 10) return '9.8 / 10';
    if (days >= 7) return '9.5 / 10';
    return '9.2 / 10';
  }

  public getCategorySpend(catName: string): { amount: number; percent: number; notes: string } {
    const total = this.itinerary?.budget_rollup?.grand_total || 312400;
    const cat = this.itinerary?.budget_rollup?.categories?.find(c => 
      c.category.toLowerCase().includes(catName.toLowerCase())
    );

    if (cat) {
      const amount = cat.estimated_total;
      const percent = Math.round((amount / total) * 100);
      return { amount, percent, notes: cat.notes || '' };
    }

    const fallbackMap: Record<string, { share: number; notes: string }> = {
      'stay': { share: 0.38, notes: 'Stays (10 Nights)' },
      'hotel': { share: 0.38, notes: 'Stays (10 Nights)' },
      'transport': { share: 0.26, notes: 'Transport & Car Rental' },
      'food': { share: 0.15, notes: 'Food & Fuel' },
      'activities': { share: 0.10, notes: 'Activities & Parks' }
    };

    const entry = fallbackMap[catName.toLowerCase()] || { share: 0.1, notes: '' };
    const amount = Math.round(total * entry.share);
    const percent = Math.round(entry.share * 100);
    return { amount, percent, notes: entry.notes };
  }

  public getTipIcon(tip: CostSavingTip): string {
    const text = (tip.title + ' ' + tip.description).toLowerCase();
    if (text.includes('fuel') || text.includes('gas') || text.includes('car') || text.includes('drive')) {
      return 'local_gas_station';
    }
    if (text.includes('bonus') || text.includes('supermarket') || text.includes('grocery') || text.includes('food')) {
      return 'shopping_cart';
    }
    return 'hot_tub';
  }

  public getPlacePhoto(place: PlaceInfo): string {
    if (place.photo_url) return place.photo_url;

    const name = (place.name || '').toLowerCase();
    if (name.includes('reynisfjara') || name.includes('black sand')) {
      return 'https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=800&auto=format&fit=crop&q=80';
    }
    if (name.includes('dyrhólaey') || name.includes('arch') || name.includes('cliff')) {
      return 'https://images.unsplash.com/photo-1529963183134-61a90db47eaf?w=800&auto=format&fit=crop&q=80';
    }
    if (name.includes('skógafoss') || name.includes('seljalandsfoss') || name.includes('waterfall') || name.includes('gullfoss')) {
      return 'https://images.unsplash.com/photo-1517411032315-54ef2cb783bb?w=800&auto=format&fit=crop&q=80';
    }
    if (name.includes('church') || name.includes('kirkja')) {
      return 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=800&auto=format&fit=crop&q=80';
    }
    if (name.includes('lagoon') || name.includes('bath') || name.includes('geothermal') || name.includes('spa')) {
      return 'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=800&auto=format&fit=crop&q=80';
    }
    if (name.includes('glacier') || name.includes('jökulsárlón') || name.includes('ice')) {
      return 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&auto=format&fit=crop&q=80';
    }

    return 'https://images.unsplash.com/photo-1504893524553-b855bce32c67?w=800&auto=format&fit=crop&q=80';
  }

  // --- Phase 11: Real Booking Integration URLs ---

  public getHotelBookingUrl(hotel?: RealHotelOffer | null, day?: DayItinerary): string {
    if (hotel?.deeplink && hotel.deeplink.startsWith('http')) {
      return hotel.deeplink;
    }
    const city = day?.city || this.activeDay.city || 'Reykjavik';
    const hotelName = hotel?.name || 'Hotel in ' + city;
    return `https://www.booking.com/searchresults.html?ss=${encodeURIComponent(hotelName + ', ' + city)}`;
  }

  public getCarBookingUrl(car?: CarEstimate | null): string {
    if (car?.deeplink && car.deeplink.startsWith('http')) {
      return car.deeplink;
    }
    return `https://www.skyscanner.net/carhire?pickup=${encodeURIComponent(this.getDestinationIata())}`;
  }

  public getPlaceMapsUrl(place: PlaceInfo): string {
    if (place.google_maps_url && place.google_maps_url.startsWith('http')) {
      return place.google_maps_url;
    }
    const city = place.city || this.activeDay.city || 'Iceland';
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(place.name + ', ' + city)}`;
  }

  public getGoogleMapsRouteUrl(): string {
    if (!this.itinerary?.days || this.itinerary.days.length === 0) {
      return 'https://www.google.com/maps/dir/Reykjavik/Vik/Hofn/Akureyri/Reykjavik';
    }
    const rawCities = this.itinerary.days.map(d => d.city.split('&')[0].trim());
    const uniqueCities = Array.from(new Set(rawCities));
    if (uniqueCities.length > 1 && uniqueCities[uniqueCities.length - 1] !== uniqueCities[0]) {
      uniqueCities.push(uniqueCities[0]); // Loop back to start
    }
    const segments = uniqueCities.map(c => encodeURIComponent(c)).join('/');
    return `https://www.google.com/maps/dir/${segments}`;
  }

  // Action handlers
  public onSearchFlightsClick(flight: RealFlightOffer): void {
    if (typeof window !== 'undefined' && flight.deeplink && flight.deeplink.startsWith('http')) {
      window.open(flight.deeplink, '_blank');
    }
    this.searchFlights.emit(flight);
  }

  public onBookStayClick(hotel: RealHotelOffer, day: DayItinerary, event?: MouseEvent): void {
    const url = this.getHotelBookingUrl(hotel, day);
    if (typeof window !== 'undefined') {
      window.open(url, '_blank');
    }
    this.bookStay.emit(hotel);
  }

  public onBookCarClick(car: CarEstimate, event?: MouseEvent): void {
    const url = this.getCarBookingUrl(car);
    if (typeof window !== 'undefined') {
      window.open(url, '_blank');
    }
    this.bookCar.emit(car);
  }

  public onSelectBlueprintClick(prompt: string): void {
    this.selectPrompt.emit(prompt);
  }

  public applySmartSwap(): void {
    this.appliedSwap.update(v => !v);
  }

  public toggleMap(): void {
    this.showMapModal.update(v => !v);
  }

  public toggleRemainingDays(): void {
    this.showRemainingDaysTable.update(v => !v);
  }
}
