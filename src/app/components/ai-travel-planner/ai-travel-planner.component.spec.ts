import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createEnvironmentInjector } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { of } from 'rxjs';
import { AiTravelPlannerComponent } from './ai-travel-planner.component';
import { TravelPlannerService } from '../../services/travel-planner.service';
import { FlightService } from '../../services/flight.service';
import { CurrencyService } from '../../services/currency.service';
import { SkyscannerApiService } from '../../services/skyscanner-api.service';
import { RealFlightOffer } from '../../models/travel-planner.model';

if (typeof localStorage === 'undefined') {
  let store: Record<string, string> = {};
  (globalThis as any).localStorage = {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; }
  };
}

describe('AiTravelPlannerComponent (Phase 11 & Phase 12)', () => {
  let component: AiTravelPlannerComponent;
  let flightService: FlightService;
  let plannerService: TravelPlannerService;

  const mockHttpClient = {
    get: vi.fn().mockReturnValue(of({ status: 'healthy', version: '0.1.0' })),
    post: vi.fn().mockReturnValue(of({
      final_itinerary: {
        id: 'plan-1',
        constraints: { destination_region: 'Iceland', duration_days: 11, budget_total: 350000, currency: 'INR', cities: ['Reykjavik'] },
        days: [],
        budget_rollup: { categories: [], grand_total: 350000, currency: 'INR', within_budget: true, remaining_buffer: 0 }
      },
      constraints: { destination_region: 'Iceland', duration_days: 11, budget_total: 350000, currency: 'INR', cities: ['Reykjavik'] },
      review_summary: 'pass',
      used_stub_mode: true
    }))
  };

  beforeEach(() => {
    const injector = createEnvironmentInjector([
      { provide: HttpClient, useValue: mockHttpClient },
      SkyscannerApiService,
      FlightService,
      CurrencyService,
      TravelPlannerService
    ], null as any);

    component = injector.runInContext(() => new AiTravelPlannerComponent());
    flightService = injector.get(FlightService);
    plannerService = injector.get(TravelPlannerService);
  });

  it('should instantiate with default prompt text and 5 agent stages', () => {
    expect(component).toBeDefined();
    expect(component.promptText()).toContain('Iceland Ring Road');
    expect(component.stages.length).toBe(5);
    expect(component.fastDemoMode()).toBe(false);
  });

  it('should update prompt text when suggestion chip is applied', () => {
    component.applySuggestion(component.suggestions[1]); // Tokyo & Kyoto
    expect(component.promptText()).toContain('Tokyo + Kyoto');
  });

  it('should toggle fast demo mode signal', () => {
    expect(component.fastDemoMode()).toBe(false);
    component.fastDemoMode.set(true);
    expect(component.fastDemoMode()).toBe(true);
  });

  it('should trigger searchFlights and switch tab to flights on deal click', () => {
    const switchTabSpy = vi.spyOn(component.switchTab, 'emit');
    const executeSearchSpy = vi.spyOn(flightService, 'executeSearch');

    const sampleFlight: RealFlightOffer = {
      id: 'fl-101',
      airline: 'Lufthansa',
      flight_number: 'LH761',
      price: 74200,
      currency: 'INR',
      origin: 'DEL',
      destination: 'KEF',
      duration_minutes: 765,
      stops: 1,
      departure: '2026-11-15T03:30:00',
      arrival: '2026-11-15T13:45:00'
    };

    component.searchFlightsForTrip(sampleFlight);

    expect(executeSearchSpy).toHaveBeenCalled();
    expect(switchTabSpy).toHaveBeenCalledWith('flights');
  });

  it('should switch tab to hotels when hotel booking has no direct deeplink', () => {
    const switchTabSpy = vi.spyOn(component.switchTab, 'emit');
    component.onBookStay({
      id: 'h-1',
      name: 'Hotel Kría',
      city: 'Vik',
      price_per_night: 180,
      total_price: 1800,
      currency: 'USD'
    });
    expect(switchTabSpy).toHaveBeenCalledWith('hotels');
  });

  it('should switch tab to cars when car booking has no direct deeplink', () => {
    const switchTabSpy = vi.spyOn(component.switchTab, 'emit');
    component.onBookCar({
      id: 'c-1',
      supplier: 'Skyscanner Car Hire',
      vehicle_name: 'Suzuki Vitara',
      category: '4x4',
      price_per_day: 45,
      total_price: 495,
      currency: 'USD',
      seats: 5,
      transmission: 'Automatic',
      is_estimate: true
    });
    expect(switchTabSpy).toHaveBeenCalledWith('cars');
  });

  it('should call plannerService.generatePlan with stubMode=true when loadInstantDemoBlueprint is called', () => {
    const spy = vi.spyOn(plannerService, 'generatePlan');
    component.loadInstantDemoBlueprint();
    expect(spy).toHaveBeenCalledWith(
      component.promptText().trim(),
      true,
      component.originCity(),
      component.travelDate()
    );
  });

  it('should clear plan when resetPlan is called', () => {
    const spy = vi.spyOn(plannerService, 'clearPlan');
    component.resetPlan();
    expect(spy).toHaveBeenCalled();
  });
});
