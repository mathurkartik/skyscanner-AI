import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CurrencyService } from '../../services/currency.service';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './footer.component.html',
  styleUrls: ['./footer.component.css']
})
export class FooterComponent {
  public readonly currencyService = inject(CurrencyService);
  public readonly currentYear = new Date().getFullYear();

  public expandedSections = new Set<string>();

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
