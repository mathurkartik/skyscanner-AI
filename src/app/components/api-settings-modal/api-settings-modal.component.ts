import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SkyscannerApiService } from '../../services/skyscanner-api.service';
import { FlightService } from '../../services/flight.service';

@Component({
  selector: 'app-api-settings-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './api-settings-modal.component.html',
  styleUrls: ['./api-settings-modal.component.css']
})
export class ApiSettingsModalComponent {
  public readonly apiService = inject(SkyscannerApiService);
  public readonly flightService = inject(FlightService);

  public inputKey = signal<string>(this.apiService.apiKey());
  public savedNotification = signal<boolean>(false);

  public close() {
    this.flightService.closeApiSettings();
    this.savedNotification.set(false);
  }

  public saveKey() {
    this.apiService.setApiKey(this.inputKey());
    this.savedNotification.set(true);
    setTimeout(() => {
      this.close();
    }, 1200);
  }

  public toggleLive(enabled: boolean) {
    this.apiService.setLiveMode(enabled);
  }
}

