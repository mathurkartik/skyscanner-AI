import { Component, inject, signal, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FlightService } from '../../services/flight.service';
import { SKYSCANNER_FAQS, INTERNATIONAL_SITES, FAQItem } from '../../data/faq.data';
import { MainTab } from '../navbar/navbar.component';

@Component({
  selector: 'app-home-feed',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './home-feed.component.html',
  styleUrls: ['./home-feed.component.css']
})
export class HomeFeedComponent {
  public readonly flightService = inject(FlightService);
  public readonly navigateTab = output<MainTab>();

  public readonly faqs = SKYSCANNER_FAQS;
  public readonly internationalSites = INTERNATIONAL_SITES;

  public readonly openFaqIds = signal<string[]>([]);
  public readonly isInternationalOpen = signal<boolean>(false);

  public leftFaqs = this.faqs.slice(0, 5);
  public rightFaqs = this.faqs.slice(5, 10);

  public toggleFaq(id: string) {
    this.openFaqIds.update(current => 
      current.includes(id) ? current.filter(x => x !== id) : [...current, id]
    );
  }

  public isFaqOpen(id: string): boolean {
    return this.openFaqIds().includes(id);
  }

  public toggleInternational() {
    this.isInternationalOpen.update(v => !v);
  }

  public openTab(tab: MainTab) {
    this.navigateTab.emit(tab);
  }
}

