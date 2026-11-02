import { Component, inject, signal, OnInit, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TravelPlannerService } from '../../services/travel-planner.service';
import { FlightService } from '../../services/flight.service';
import { CurrencyService } from '../../services/currency.service';
import { RealFlightOffer, RealHotelOffer, CarEstimate } from '../../models/travel-planner.model';
import { POPULAR_AIRPORTS } from '../../data/airports.data';
import { ItineraryDisplayComponent } from '../itinerary-display/itinerary-display.component';
import { MainTab } from '../navbar/navbar.component';

interface SuggestionChip {
  label: string;
  flag: string;
  prompt: string;
}

interface AgentStage {
  name: string;
  role: string;
  icon: string;
  detail: string;
}

@Component({
  selector: 'app-ai-travel-planner',
  standalone: true,
  imports: [CommonModule, FormsModule, ItineraryDisplayComponent],
  templateUrl: './ai-travel-planner.component.html',
  styleUrls: ['./ai-travel-planner.component.css']
})
export class AiTravelPlannerComponent implements OnInit {
  public readonly plannerService = inject(TravelPlannerService);
  public readonly flightService = inject(FlightService);
  public readonly currencyService = inject(CurrencyService);

  @Output() public switchTab = new EventEmitter<MainTab>();

  public promptText = signal<string>(
    'Plan an 11-day Iceland Ring Road road trip starting from Nagpur, ₹3.5L budget, waterfalls & geothermal baths, love nature and scenic drives'
  );

  public originCity = signal<string>('');
  public travelDate = signal<string>('');
  public showOriginSuggestions = signal<boolean>(false);

  public readonly popularOrigins = [
    'New York', 'London', 'Dubai', 'Singapore', 'Mumbai',
    'Delhi', 'Tokyo', 'Sydney', 'Los Angeles', 'San Francisco',
    'Toronto', 'Paris', 'Frankfurt', 'Hong Kong', 'Bangkok'
  ];

  public filteredOrigins(): string[] {
    const query = this.originCity().toLowerCase();
    if (!query) return this.popularOrigins.slice(0, 8);
    return this.popularOrigins.filter(c => c.toLowerCase().includes(query));
  }

  public selectOrigin(city: string): void {
    this.originCity.set(city);
    this.showOriginSuggestions.set(false);
  }

  public hideOriginSuggestionsDelayed(): void {
    setTimeout(() => this.showOriginSuggestions.set(false), 200);
  }

  public get minDate(): string {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return d.toISOString().split('T')[0];
  }

  // Fast demo mode toggle (200ms pre-cached response vs live multi-agent API)
  public fastDemoMode = signal<boolean>(false);

  // Progress tracking signals
  public progressMessage = signal<string>('Initializing multi-agent orchestrator...');
  public currentStageIndex = signal<number>(0);
  public elapsedSeconds = signal<number>(0);

  private progressInterval: any = null;
  private timerInterval: any = null;

  public readonly stages: AgentStage[] = [
    { name: 'Orchestrator', role: 'Deconstruction', icon: 'hub', detail: 'Extracting destination, duration, budget, and travel preferences...' },
    { name: 'Destination Agent', role: 'Attractions', icon: 'map', detail: 'Querying Google Places for authentic attractions and operating hours...' },
    { name: 'Logistics Agent', role: 'Transit & Stays', icon: 'commute', detail: 'Searching Skyscanner for real flights & Booking.com for available hotels...' },
    { name: 'Budget Agent', role: 'Cost Optimization', icon: 'account_balance_wallet', detail: 'Calibrating driving times, car rentals, and auditing budget limits...' },
    { name: 'Review Agent', role: 'Strategic Audit', icon: 'verified', detail: 'Validating day pacing, crowd avoidance, and geocoded route pins...' }
  ];

  public readonly suggestions: SuggestionChip[] = [
    {
      flag: '🇮🇸',
      label: 'Iceland Ring Road',
      prompt: 'Plan an 11-day Iceland Ring Road road trip starting from Nagpur, ₹3.5L budget, waterfalls & geothermal baths, love nature and scenic drives'
    },
    {
      flag: '🇯🇵',
      label: 'Tokyo & Kyoto',
      prompt: 'Plan a 5-day trip to Japan: Tokyo + Kyoto, $3,000 budget. Authentic food and quiet morning temples, avoid heavy crowds.'
    },
    {
      flag: '🇨🇭',
      label: 'Swiss Alps by Train',
      prompt: 'Plan a 7-day Switzerland scenic train trip through Zurich, Lucerne, and Interlaken, €2,500 budget, mountain hiking.'
    },
    {
      flag: '🇮🇳',
      label: 'Varanasi & Rishikesh',
      prompt: 'Plan a 6-day heritage and spiritual journey to Varanasi and Rishikesh, ₹45,000 budget, morning Ganga aarti and yoga retreats.'
    },
    {
      flag: '🇦🇺',
      label: 'Melbourne & Coast',
      prompt: 'Plan a 6-day trip to Melbourne and Great Ocean Road, $2,200 budget, coastal sightseeing, coffee culture, and wildlife.'
    }
  ];

  ngOnInit(): void {
    this.plannerService.checkHealth().subscribe({
      next: () => {},
      error: () => {}
    });
  }

  public applySuggestion(chip: SuggestionChip): void {
    this.promptText.set(chip.prompt);
  }

  public onSelectPrompt(prompt: string): void {
    this.promptText.set(prompt);
    this.generatePlan();
  }

  public generatePlan(forceStub = false): void {
    const text = this.promptText().trim();
    if (!text || this.plannerService.isLoading()) return;

    const useStub = forceStub || this.fastDemoMode();
    this.startProgressSimulation();

    const origin = this.originCity().trim();
    const date = this.travelDate().trim();

    this.plannerService.generatePlan(text, useStub, origin, date, 'USD').subscribe({
      next: () => {
        this.stopProgressSimulation();
      },
      error: () => {
        this.stopProgressSimulation();
      }
    });
  }

  public loadInstantDemoBlueprint(): void {
    this.generatePlan(true);
  }

  public retryPlan(): void {
    this.generatePlan();
  }

  public resetPlan(): void {
    this.plannerService.clearPlan();
  }

  // --- Phase 11: Real In-App Booking Handlers ---

  public searchFlightsForTrip(flight: RealFlightOffer): void {
    const destAirport = POPULAR_AIRPORTS.find(a => a.code === flight.destination) || POPULAR_AIRPORTS[0];
    const originAirport = POPULAR_AIRPORTS.find(a => a.code === flight.origin) || POPULAR_AIRPORTS[0];

    this.flightService.executeSearch({
      tripType: 'round-trip',
      origin: originAirport,
      destination: destAirport,
      departDate: flight.departure ? flight.departure.split('T')[0] : '2026-11-15',
      returnDate: flight.arrival ? flight.arrival.split('T')[0] : '2026-11-22',
      adults: 1,
      children: 0,
      cabinClass: 'economy',
      directOnly: flight.stops === 0
    }, true);

    // Switch to flights view in top navbar
    this.switchTab.emit('flights');
  }

  public onBookStay(hotel: RealHotelOffer): void {
    if (typeof window !== 'undefined' && hotel.deeplink && hotel.deeplink.startsWith('http')) {
      window.open(hotel.deeplink, '_blank');
    } else {
      this.switchTab.emit('hotels');
    }
  }

  public onBookCar(car: CarEstimate): void {
    if (typeof window !== 'undefined' && car.deeplink && car.deeplink.startsWith('http')) {
      window.open(car.deeplink, '_blank');
    } else {
      this.switchTab.emit('cars');
    }
  }

  private startProgressSimulation(): void {
    this.elapsedSeconds.set(0);
    this.currentStageIndex.set(0);
    this.progressMessage.set(this.stages[0].detail);

    if (this.timerInterval) clearInterval(this.timerInterval);
    this.timerInterval = setInterval(() => {
      this.elapsedSeconds.update(s => s + 1);
    }, 1000);

    if (this.progressInterval) clearInterval(this.progressInterval);
    this.progressInterval = setInterval(() => {
      this.currentStageIndex.update(idx => {
        const next = Math.min(idx + 1, this.stages.length - 1);
        this.progressMessage.set(this.stages[next].detail);
        return next;
      });
    }, 4000);
  }

  private stopProgressSimulation(): void {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
      this.progressInterval = null;
    }
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }
}
