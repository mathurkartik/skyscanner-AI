import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createEnvironmentInjector } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { of } from 'rxjs';
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
});
