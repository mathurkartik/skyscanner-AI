import { Component, inject, signal, output } from '@angular/core';
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
export class NavbarComponent {
  public readonly currencyService = inject(CurrencyService);
  public readonly favoritesService = inject(FavoritesService);
  public readonly flightService = inject(FlightService);

  public readonly activeTab = signal<MainTab>('ai');
  public readonly tabChanged = output<MainTab>();

  public readonly isLocaleModalOpen = signal<boolean>(false);
  public readonly isLoginModalOpen = signal<boolean>(false);
  public readonly isHelpModalOpen = signal<boolean>(false);
  public readonly isFavoritesOpen = signal<boolean>(false);
  public readonly isLoggedIn = signal<boolean>(false);
  public readonly userEmail = signal<string>('traveler@example.com');

  public setTab(tab: MainTab) {
    this.activeTab.set(tab);
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
