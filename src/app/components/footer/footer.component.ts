import { Component, inject, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CurrencyService } from '../../services/currency.service';
import { MainTab } from '../navbar/navbar.component';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './footer.component.html',
  styleUrls: ['./footer.component.css']
})
export class FooterComponent {
  public readonly currencyService = inject(CurrencyService);
  public readonly navigateTab = output<MainTab>();
  public readonly currentYear = new Date().getFullYear();

  public expandedSections = new Set<string>();

  public onNavigate(tab: MainTab, event?: Event): void {
    if (event) event.preventDefault();
    this.navigateTab.emit(tab);
  }

  public toggleSection(name: string): void {
    if (this.expandedSections.has(name)) {
      this.expandedSections.delete(name);
    } else {
      this.expandedSections.add(name);
    }
  }

  public isExpanded(name: string): boolean {
    return this.expandedSections.has(name);
  }
}
