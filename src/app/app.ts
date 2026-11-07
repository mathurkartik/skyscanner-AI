import { Component, inject, signal, OnInit, OnDestroy } from '@angular/core';
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
export class App implements OnInit, OnDestroy {
  public readonly flightService = inject(FlightService);
  public readonly currentTab = signal<MainTab>('ai');

  private onHashChangeBound = () => this.syncTabFromHash();

  public ngOnInit(): void {
    if (typeof window !== 'undefined') {
      this.syncTabFromHash();
      window.addEventListener('hashchange', this.onHashChangeBound);
    }
  }

  public ngOnDestroy(): void {
    if (typeof window !== 'undefined') {
      window.removeEventListener('hashchange', this.onHashChangeBound);
    }
  }

  private syncTabFromHash(): void {
    if (typeof window === 'undefined') return;
    const hash = window.location.hash.replace('#', '').toLowerCase();
    const validTabs: MainTab[] = ['flights', 'hotels', 'cars', 'explore', 'ai'];
    if (validTabs.includes(hash as MainTab)) {
      this.currentTab.set(hash as MainTab);
    }
  }

  public onTabChange(tab: MainTab) {
    this.currentTab.set(tab);
    if (typeof window !== 'undefined') {
      window.location.hash = tab;
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  public navigateToExplore() {
    this.onTabChange('explore');
  }

  public onDestinationChosen() {
    this.onTabChange('flights');
  }
}
