import { Component, inject, signal, output, input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CurrencyService } from '../../services/currency.service';
import { FavoritesService } from '../../services/favorites.service';
import { FlightService } from '../../services/flight.service';

export type MainTab = 'flights' | 'hotels' | 'cars' | 'explore' | 'ai';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './navbar.component.html',
  styleUrls: ['./navbar.component.css']
})
export class NavbarComponent implements OnInit {
  public readonly currencyService = inject(CurrencyService);
  public readonly favoritesService = inject(FavoritesService);
  public readonly flightService = inject(FlightService);

  // AG-032: Receive activeTab from App component input to eliminate tab state drift
  public readonly activeTab = input<MainTab>('ai');
  public readonly tabChanged = output<MainTab>();

  public readonly isLocaleModalOpen = signal<boolean>(false);
  public readonly isLoginModalOpen = signal<boolean>(false);
  public readonly isHelpModalOpen = signal<boolean>(false);
  public readonly isFavoritesOpen = signal<boolean>(false);
  public readonly isLoggedIn = signal<boolean>(false);
  public readonly userEmail = signal<string>('traveler@example.com');
  public readonly isDebugMode = signal<boolean>(false);

  private logoClicks = 0;
  private lastLogoClickTime = 0;

  public ngOnInit(): void {
    if (typeof window !== 'undefined') {
      if (window.location.hash.includes('debug')) {
        this.isDebugMode.set(true);
      }
      window.addEventListener('hashchange', () => {
        if (window.location.hash.includes('debug')) {
          this.isDebugMode.set(true);
        }
      });
    }
  }

  public onLogoClick(): void {
    const now = Date.now();
    if (now - this.lastLogoClickTime < 600) {
      this.logoClicks++;
      if (this.logoClicks >= 3) {
        this.isDebugMode.set(true);
        this.flightService.openApiSettings();
        this.logoClicks = 0;
      }
    } else {
      this.logoClicks = 1;
    }
    this.lastLogoClickTime = now;
    this.setTab('ai');
  }

  public setTab(tab: MainTab) {
    if (tab === 'flights') {
      this.flightService.goToHomepage();
    }
    this.tabChanged.emit(tab);
  }

  public openAi() {
    this.setTab('ai');
  }

  public toggleLocaleModal() {
    this.isLocaleModalOpen.update(v => !v);
  }

  public toggleLoginModal() {
    this.isLoginModalOpen.update(v => !v);
  }

  public toggleHelpModal() {
    this.isHelpModalOpen.update(v => !v);
  }

  public toggleFavorites() {
    this.isFavoritesOpen.update(v => !v);
  }

  public selectCurrency(code: string) {
    this.currencyService.setCurrency(code);
    this.isLocaleModalOpen.set(false);
  }

  public handleLogin() {
    this.isLoggedIn.set(true);
    this.isLoginModalOpen.set(false);
  }

  public handleLogout() {
    this.isLoggedIn.set(false);
  }
}
