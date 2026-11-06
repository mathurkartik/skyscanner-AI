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

    const payload: PlanRequest = {
      request: prompt.trim(),
      stub_mode: stubMode,
      ...(originCity ? { origin_city: originCity.trim() } : {}),
      ...(startDate ? { start_date: startDate.trim() } : {}),
      ...(currency ? { currency: currency.trim() } : {})
    };

    return this.http.post<PlanResponse>(`${this.baseUrl}/api/plan`, payload).pipe(
      timeout(150000),
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

  private handleError(error: any): void {
    if (error.name === 'TimeoutError') {
      this.errorMessage.set('Our servers are warming up. This can take up to 60 seconds for the first request. Please try again or load an instant blueprint.');
    } else if (error instanceof HttpErrorResponse) {
      if (error.status === 0) {
        this.errorMessage.set('Cannot connect to the AI planner backend at ' + this.baseUrl + '. Make sure the backend server is running on port 8000.');
      } else if (error.error && error.error.detail) {
        if (typeof error.error.detail === 'string') {
          this.errorMessage.set(error.error.detail);
        } else if (error.error.detail.message) {
          this.errorMessage.set(error.error.detail.message);
        } else if (Array.isArray(error.error.detail) && error.error.detail[0]?.msg) {
          this.errorMessage.set(error.error.detail[0].msg);
        } else {
          this.errorMessage.set('Request validation failed. Please check your travel constraints and try again.');
        }
      } else {
        this.errorMessage.set(`Backend error (${error.status}): ${error.message || 'Please try again'}`);
      }
    } else {
      this.errorMessage.set('An unexpected error occurred while generating your itinerary.');
    }
  }
}

