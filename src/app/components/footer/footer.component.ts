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
}
