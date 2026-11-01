import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavbarComponent, MainTab } from './components/navbar/navbar.component';
import { FlightSearchComponent } from './components/flight-search/flight-search.component';
import { HomeFeedComponent } from './components/home-feed/home-feed.component';
import { FlightResultsComponent } from './components/flight-results/flight-results.component';
import { HotelSearchComponent } from './components/hotel-search/hotel-search.component';
import { CarSearchComponent } from './components/car-search/car-search.component';
import { ExploreEverywhereComponent } from './components/explore-everywhere/explore-everywhere.component';
import { AiTravelPlannerComponent } from './components/ai-travel-planner/ai-travel-planner.component';
import { ApiSettingsModalComponent } from './components/api-settings-modal/api-settings-modal.component';
import { FooterComponent } from './components/footer/footer.component';
import { FlightService } from './services/flight.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    NavbarComponent,
    FlightSearchComponent,
    HomeFeedComponent,
    FlightResultsComponent,
    HotelSearchComponent,
    CarSearchComponent,
    ExploreEverywhereComponent,
    AiTravelPlannerComponent,
    ApiSettingsModalComponent,
    FooterComponent
  ],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  public readonly flightService = inject(FlightService);
  public readonly currentTab = signal<MainTab>('flights');

  public onTabChange(tab: MainTab) {
    this.currentTab.set(tab);
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  public navigateToExplore() {
    this.currentTab.set('explore');
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  public onDestinationChosen() {
    this.currentTab.set('flights');
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }
}
