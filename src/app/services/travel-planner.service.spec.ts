import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createEnvironmentInjector } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { of, throwError } from 'rxjs';
import { TravelPlannerService } from './travel-planner.service';
import { PlanResponse } from '../models/travel-planner.model';

describe('TravelPlannerService', () => {
  let service: TravelPlannerService;
  let mockHttpClient: { post: any; get: any };

  beforeEach(() => {
    mockHttpClient = {
      post: vi.fn(),
      get: vi.fn()
    };

    const injector = createEnvironmentInjector([
      { provide: HttpClient, useValue: mockHttpClient },
      TravelPlannerService
    ], null as any);

    service = injector.get(TravelPlannerService);
  });

  it('should instantiate service with initial state', () => {
    expect(service).toBeDefined();
    expect(service.isLoading()).toBe(false);
    expect(service.errorMessage()).toBeNull();
    expect(service.currentItinerary()).toBeNull();
  });

  it('should reset plan on clearPlan', () => {
    service.clearPlan();
    expect(service.currentItinerary()).toBeNull();
    expect(service.errorMessage()).toBeNull();
    expect(service.isLoading()).toBe(false);
  });

  it('should call backend API and update state on generatePlan', async () => {
    const mockResponse: any = {
      trace_id: 'test-plan-123',
      final_itinerary: {
        id: 'test-plan-123',
        destination: 'Reykjavik, Iceland',
        constraints: { destination_region: 'Reykjavik, Iceland' }
      }
    };

    mockHttpClient.post.mockReturnValue(of(mockResponse));

    service.generatePlan('5 days in Iceland').subscribe((res) => {
      expect(res.trace_id).toBe('test-plan-123');
    });

    expect(mockHttpClient.post).toHaveBeenCalledTimes(1);
    expect(service.isLoading()).toBe(false);
    expect(service.activePlanId()).toBe('test-plan-123');
    expect(service.currentItinerary()?.id).toBe('test-plan-123');
  });

  it('should sanitize raw LLM JSON and model errors into user-friendly message (MF-1)', () => {
    const rawError = new HttpErrorResponse({
      status: 500,
      error: {
        detail: '404 {"error":{"message":"The model llama-3.3-70b-versatile does not exist or you do not have access to it."}}'
      }
    });
    mockHttpClient.post.mockReturnValue(throwError(() => rawError));

    service.generatePlan('5 days in Japan').subscribe({ error: () => {} });

    expect(service.errorMessage()).toBe("I'm having trouble connecting right now. Please try again in a moment.");
    expect(service.errorMessage()).not.toContain('llama');
    expect(service.errorMessage()).not.toContain('404');
  });

  it('should preserve clean validation messages while hiding technical 4xx/0 errors (MF-1)', () => {
    const constraintErr = new HttpErrorResponse({
      status: 400,
      error: { detail: { message: 'Please specify how many days your trip will last.' } }
    });
    mockHttpClient.post.mockReturnValue(throwError(() => constraintErr));
    service.generatePlan('Japan trip').subscribe({ error: () => {} });
    expect(service.errorMessage()).toBe('Please specify how many days your trip will last.');

    const netErr = new HttpErrorResponse({ status: 0, statusText: 'Unknown Error' });
    mockHttpClient.post.mockReturnValue(throwError(() => netErr));
    service.generatePlan('Japan trip').subscribe({ error: () => {} });
    expect(service.errorMessage()).toBe("I'm having trouble connecting right now. Please try again in a moment.");
  });

  it('should reset loading state on cancelPlan (SF-1)', () => {
    service.isLoading.set(true);
    service.cancelPlan();
    expect(service.isLoading()).toBe(false);
    expect(service.errorMessage()).toBeNull();
  });
});
