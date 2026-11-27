import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, timeout, tap } from 'rxjs/operators';
import { PlanRequest, PlanResponse, FinalItinerary } from '../models/travel-planner.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class TravelPlannerService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  // Reactive state signals
  public readonly isLoading = signal<boolean>(false);
  public readonly errorMessage = signal<string | null>(null);
  public readonly currentItinerary = signal<FinalItinerary | null>(null);
  public readonly activePlanId = signal<string | null>(null);

  /**
   * Request multi-agent AI travel plan from the FastAPI backend.
   * Timeout set to 90 seconds to accommodate multi-agent research pipeline.
   */
  public generatePlan(
    prompt: string,
    stubMode: boolean = false,
    originCity?: string,
    startDate?: string,
    currency?: string
  ): Observable<PlanResponse> {
    this.isLoading.set(true);
    this.errorMessage.set(null);
    // AG-022: Clear previous itinerary to prevent simultaneous Loading + Results display
    this.currentItinerary.set(null);

    const payload: PlanRequest = {
      request: prompt.trim(),
      stub_mode: stubMode,
      ...(originCity ? { origin_city: originCity.trim() } : {}),
      ...(startDate ? { start_date: startDate.trim() } : {}),
      ...(currency ? { currency: currency.trim() } : {})
    };

    return this.http.post<PlanResponse>(`${this.baseUrl}/api/plan`, payload).pipe(
      timeout(210000),
      tap({
        next: (response) => {
          this.isLoading.set(false);
          this.activePlanId.set(response.trace_id);
          this.currentItinerary.set(response.final_itinerary);
        },
        error: (err) => {
          this.isLoading.set(false);
          this.handleError(err);
        }
      }),
      catchError((error) => {
        return throwError(() => error);
      })
    );
  }

  /**
   * Health check for backend connectivity.
   */
  public checkHealth(): Observable<any> {
    return this.http.get(`${this.baseUrl}/health`).pipe(
      timeout(5000),
      catchError((err) => throwError(() => err))
    );
  }

  public clearPlan(): void {
    this.currentItinerary.set(null);
    this.errorMessage.set(null);
    this.isLoading.set(false);
  }

  public cancelPlan(): void {
    this.isLoading.set(false);
    this.errorMessage.set(null);
  }

  private sanitizeUserErrorMessage(raw: string): string {
    const friendlyFallback = "I'm having trouble connecting right now. Please try again in a moment.";
    if (!raw || typeof raw !== 'string') {
      return friendlyFallback;
    }

    const trimmed = raw.trim();
    const technicalPattern = /(\{|\}|traceback|runtimeerror|exception|http failure|https?:\/\/|localhost|\b(?:400|401|403|404|422|429|500|502|503|504)\b|groq|llama|gemini|gpt-oss|openai|duffel|rapidapi|rate_limit|unauthenticated|not_found|api key)/i;
    if (technicalPattern.test(trimmed)) {
      return friendlyFallback;
    }

    return trimmed;
  }

  private handleError(error: any): void {
    const friendlyFallback = "I'm having trouble connecting right now. Please try again in a moment.";

    if (error.name === 'TimeoutError') {
      this.errorMessage.set('This trip is taking longer than expected. Please try again in a moment or load an instant blueprint.');
    } else if (error instanceof HttpErrorResponse) {
      if (error.status === 0 || error.status >= 500) {
        this.errorMessage.set(friendlyFallback);
      } else if (error.error && error.error.detail) {
        if (typeof error.error.detail === 'string') {
          this.errorMessage.set(this.sanitizeUserErrorMessage(error.error.detail));
        } else if (error.error.detail.message) {
          this.errorMessage.set(this.sanitizeUserErrorMessage(error.error.detail.message));
        } else if (Array.isArray(error.error.detail) && error.error.detail[0]?.msg) {
          this.errorMessage.set(this.sanitizeUserErrorMessage(error.error.detail[0].msg));
        } else {
          this.errorMessage.set('Please check your trip details (destination, duration, and budget) and try again.');
        }
      } else {
        this.errorMessage.set(friendlyFallback);
      }
    } else {
      this.errorMessage.set(friendlyFallback);
    }
  }
}

