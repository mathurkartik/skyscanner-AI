"""
Budget Agent - Phase 4c.
Ensures plan stays within budget constraints.
Uses LLM for city-specific cost estimation instead of static price bands.
"""

import json
from typing import List, Optional, Dict

from ..models import (
    TravelConstraints,
    BudgetBreakdown,
    BudgetCategory,
    BudgetViolation,
    SuggestedSwap,
    CostBand,
    LogisticsOutput,
)
from ..utils.currency import convert_currency, from_usd, to_usd


class BudgetAgent:
    """
    Analyzes costs and ensures budget compliance.
    Uses LLM knowledge for city-specific pricing estimates and calibrates with real flight/hotel data.
    """

    def __init__(self, tool_router=None, llm_client=None):
        self.tool_router = tool_router
        self.llm_client = llm_client

    @staticmethod
    def _extract_json_content(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if "```" in text:
                text = text[:text.rfind("```")]
            text = text.strip()
        brace = text.find("{")
        if brace > 0:
            text = text[brace:]
        return text

    async def analyze(self, constraints: TravelConstraints, logistics_output: Optional[LogisticsOutput] = None) -> BudgetBreakdown:
        """Generate budget breakdown from constraints calibrated with real data."""
        breakdown = None
        if self.llm_client:
            try:
                breakdown = await self._llm_analyze(constraints)
            except Exception as e:
                print(f"LLM budget analysis failed: {e}")

        if not breakdown:
            breakdown = await self._fallback_analyze(constraints)

        # Calibrate with real logistics prices if available
        if logistics_output:
            breakdown = self._calibrate_with_real_data(breakdown, constraints, logistics_output)

        return breakdown

    def _calibrate_with_real_data(
        self,
        breakdown: BudgetBreakdown,
        constraints: TravelConstraints,
        logistics_output: LogisticsOutput
    ) -> BudgetBreakdown:
        """Enrich and calibrate budget categories with actual flight and hotel quotes using canonical FX rates (AG-003, AG-004)."""
        target_curr = (constraints.currency or "USD").upper().strip()
        
        # 1. Calibrate Flights / Transport (AG-019: Keep genuine flight cost)
        flight_cost_curr = 0.0
        flight_notes = "Real flight quotes from Skyscanner/Duffel inventory"
        if logistics_output.flight_offers:
            cheapest_flight = min(logistics_output.flight_offers, key=lambda f: f.price)
            # AG-004: Convert safely from flight quote currency to target currency (avoids 83x double conversion)
            flight_curr = getattr(cheapest_flight, "currency", "USD") or "USD"
            flight_cost_curr = round(convert_currency(cheapest_flight.price, flight_curr, target_curr), 2)
            if constraints.budget_total > 0 and flight_cost_curr > (constraints.budget_total * 0.50):
                flight_notes = f"Real flight quotes ({constraints.currency} {flight_cost_curr:.2f}) exceed 50% of total budget"

        # 2. Calibrate Hotel Stay
        hotel_total_curr = 0.0
        hotel_swaps: List[SuggestedSwap] = []
        for city, hotels in logistics_output.hotels_by_city.items():
            if hotels:
                selected_hotel = hotels[0]
                # AG-004: Convert safely from hotel quote currency to target currency
                hotel_curr = getattr(selected_hotel, "currency", "USD") or "USD"
                hotel_total_curr += round(convert_currency(selected_hotel.total_price, hotel_curr, target_curr), 2)
                # If cheaper alternatives exist, create swap
                if len(hotels) > 1:
                    cheapest_hotel = min(hotels, key=lambda h: h.price_per_night)
                    comparison_hotel = selected_hotel if cheapest_hotel.name != selected_hotel.name else max(hotels, key=lambda h: h.price_per_night)
                    if cheapest_hotel.name != comparison_hotel.name and comparison_hotel.price_per_night > cheapest_hotel.price_per_night:
                        diff = comparison_hotel.price_per_night - cheapest_hotel.price_per_night
                        h_curr = getattr(comparison_hotel, "currency", "USD") or "USD"
                        savings = round(convert_currency(diff, h_curr, target_curr), 2)
                        hotel_swaps.append(SuggestedSwap(
                            original_item=f"Stay at {comparison_hotel.name} ({city})",
                            suggested_alternative=f"Switch to {cheapest_hotel.name} ({city})",
                            savings_estimate=savings,
                            rationale=f"Save {savings} {constraints.currency}/night with high guest rating ({cheapest_hotel.guest_rating}★)"
                        ))
                    elif len(hotels) > 1:
                        alt_hotel = hotels[1]
                        diff = max(10.0, selected_hotel.price_per_night * 0.15)
                        h_curr = getattr(selected_hotel, "currency", "USD") or "USD"
                        savings = round(convert_currency(diff, h_curr, target_curr), 2)
                        hotel_swaps.append(SuggestedSwap(
                            original_item=f"Stay at {selected_hotel.name} ({city})",
                            suggested_alternative=f"Switch to {alt_hotel.name} ({city})",
                            savings_estimate=savings,
                            rationale=f"Alternative high-value option in {city} with {alt_hotel.guest_rating}★ guest rating"
                        ))

        # 3. AG-008: Holistic combined cap on Flights + Lodging (70% combined cap)
        hotel_notes = "Real rates from Booking.com inventory"
        if constraints.budget_total > 0:
            max_combined_fixed = constraints.budget_total * 0.70
            combined_fixed = flight_cost_curr + hotel_total_curr
            if combined_fixed > max_combined_fixed:
                if hotel_swaps:
                    hotel_notes = "Calibrated with cost-effective lodging alternatives"
                # Cap hotel so combined fixed costs stay within 70% of budget
                # (ensuring at least 30% remains for food, activities, and transit)
                max_hotel_allowed = max(constraints.budget_total * 0.20, max_combined_fixed - flight_cost_curr)
                if hotel_total_curr > max_hotel_allowed:
                    hotel_total_curr = round(max_hotel_allowed, 2)

        # Update or populate categories so rollup is always complete
        cat_map = {c.category: c for c in breakdown.categories}
        
        if hotel_total_curr > 0:
            cat_map["stay"] = BudgetCategory(
                category="stay",
                estimated_total=hotel_total_curr,
                currency=constraints.currency,
                notes=hotel_notes
            )
        elif "stay" not in cat_map:
            cat_map["stay"] = BudgetCategory(
                category="stay",
                estimated_total=round(constraints.budget_total * 0.35, 2),
                currency=constraints.currency,
                notes="Estimated accommodations allocation"
            )

        if flight_cost_curr > 0:
            cat_map["transport"] = BudgetCategory(
                category="transport",
                estimated_total=flight_cost_curr,
                currency=constraints.currency,
                notes=flight_notes
            )
        elif "transport" not in cat_map:
            cat_map["transport"] = BudgetCategory(
                category="transport",
                estimated_total=round(constraints.budget_total * 0.20, 2),
                currency=constraints.currency,
                notes="Estimated intercity and local transit"
            )

        # Baseline discretionary allocations (guaranteeing min 30% for food, activities, buffer when under 70% cap)
        fixed_sum = cat_map["stay"].estimated_total + cat_map["transport"].estimated_total
        remaining_discretionary = max(0.0, constraints.budget_total - fixed_sum) if constraints.budget_total > 0 else 0.0

        if remaining_discretionary > 0:
            cat_map["food"] = BudgetCategory(
                category="food",
                estimated_total=round(remaining_discretionary * 0.50, 2),
                currency=constraints.currency,
                notes="Estimated daily meals and dining"
            )
            cat_map["activities"] = BudgetCategory(
                category="activities",
                estimated_total=round(remaining_discretionary * 0.35, 2),
                currency=constraints.currency,
                notes="Estimated attraction tickets and tours"
            )
            cat_map["buffer"] = BudgetCategory(
                category="buffer",
                estimated_total=round(remaining_discretionary * 0.15, 2),
                currency=constraints.currency,
                notes="Contingency buffer"
            )
        else:
            if "food" not in cat_map:
                cat_map["food"] = BudgetCategory(
                    category="food",
                    estimated_total=round(constraints.budget_total * 0.15, 2) if constraints.budget_total > 0 else 100.0,
                    currency=constraints.currency,
                    notes="Estimated daily meals and dining"
                )
            if "activities" not in cat_map:
                cat_map["activities"] = BudgetCategory(
                    category="activities",
                    estimated_total=round(constraints.budget_total * 0.10, 2) if constraints.budget_total > 0 else 50.0,
                    currency=constraints.currency,
                    notes="Estimated attraction tickets and tours"
                )
            if "buffer" not in cat_map:
                cat_map["buffer"] = BudgetCategory(
                    category="buffer",
                    estimated_total=round(constraints.budget_total * 0.05, 2) if constraints.budget_total > 0 else 25.0,
                    currency=constraints.currency,
                    notes="Contingency buffer"
                )

        # Standard category order
        order = ["stay", "transport", "food", "activities", "buffer"]

        updated_categories = [cat_map[k] for k in order if k in cat_map]
        for k, v in cat_map.items():
            if k not in order:
                updated_categories.append(v)

        grand_total = round(sum(c.estimated_total for c in updated_categories), 2)
        within_budget = (grand_total <= constraints.budget_total) if constraints.budget_total > 0 else True
        violations = list(breakdown.violations or [])
        if not within_budget:
            violations.append(BudgetViolation(
                category="total",
                estimated=grand_total,
                limit=constraints.budget_total,
                over_by=round(grand_total - constraints.budget_total, 2)
            ))
            if constraints.budget_total > 0 and fixed_sum > (constraints.budget_total * 0.70):
                violations.append(BudgetViolation(
                    category="fixed_costs",
                    estimated=round(fixed_sum, 2),
                    limit=round(constraints.budget_total * 0.70, 2),
                    over_by=round(fixed_sum - (constraints.budget_total * 0.70), 2)
                ))

        all_swaps = hotel_swaps + breakdown.suggested_swaps

        return BudgetBreakdown(
            categories=updated_categories,
            grand_total=grand_total,
            currency=constraints.currency,
            within_budget=within_budget,
            remaining_buffer=round(max(0.0, constraints.budget_total - grand_total), 2),
            violations=violations,
            suggested_swaps=all_swaps[:5]
        )

    async def _llm_analyze(self, constraints: TravelConstraints) -> BudgetBreakdown:
        """Use LLM to generate city-specific budget estimates."""
        system_prompt = f"""You are a travel budget expert. Estimate realistic costs for a trip.

Respond with valid JSON:
{{
  "categories": [
    {{
      "category": "stay|food|transport|activities",
      "city": "city name",
      "estimated_total": number in {constraints.currency},
      "notes": "brief explanation"
    }}
  ],
  "grand_total": number in {constraints.currency},
  "within_budget": boolean,
  "swap_suggestions": [
    {{
      "original_item": "what to change",
      "suggested_alternative": "cheaper option",
      "savings_estimate": number in {constraints.currency},
      "rationale": "why this works"
    }}
  ]
}}

Rules:
- All amounts in {constraints.currency}
- For each city, provide stay, food, transport, and activities categories
- Use realistic local prices for {constraints.currency}
- If over budget, suggest at most 3 specific swaps
- Keep each note under 12 words (mention real hotel tiers, food types, transport modes)"""

        user_prompt = f"""Estimate costs for:
- Destination: {constraints.destination_region}
- Cities: {', '.join(constraints.cities)}
- Duration: {constraints.duration_days} days
- Budget: {constraints.budget_total} {constraints.currency}
- Preferences: {', '.join(constraints.preferences) if constraints.preferences else 'general'}"""

        content = await self.llm_client.chat_with_retry(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=3000
        )

        content = self._extract_json_content(content)
        data = json.loads(content)

        CATEGORY_MAP = {
            "accommodation": "stay", "hotel": "stay", "lodging": "stay", "housing": "stay", "stays": "stay",
            "flight": "transport", "flights": "transport", "train": "transport", "bus": "transport", "transit": "transport", "car": "transport", "transportation": "transport",
            "dining": "food", "meals": "food", "restaurant": "food", "eating": "food", "groceries": "food",
            "sightseeing": "activities", "tours": "activities", "entertainment": "activities", "attractions": "activities", "experiences": "activities",
            "miscellaneous": "buffer", "misc": "buffer", "other": "buffer", "emergency": "buffer", "contingency": "buffer", "tips": "buffer"
        }
        categories = []
        for cat in data.get("categories", []):
            raw_c = str(cat.get("category", "")).lower().strip()
            mapped_c = CATEGORY_MAP.get(raw_c, raw_c)
            if mapped_c not in ("stay", "transport", "food", "activities", "buffer"):
                mapped_c = "activities"
            categories.append(BudgetCategory(
                category=mapped_c,
                estimated_total=round(float(cat.get("estimated_total", 0.0)), 2),
                currency=constraints.currency,
                notes=cat.get("notes", "")
            ))

        calculated_total = round(sum(c.estimated_total for c in categories), 2)
        grand_total = calculated_total
        within_budget = grand_total <= constraints.budget_total

        violations = []
        if not within_budget:
            over_by = grand_total - constraints.budget_total
            violations.append(BudgetViolation(
                category="total", estimated=grand_total,
                limit=constraints.budget_total, over_by=over_by
            ))

        suggested_swaps = []
        for swap in data.get("swap_suggestions", []):
            suggested_swaps.append(SuggestedSwap(
                original_item=swap.get("original_item", ""),
                suggested_alternative=swap.get("suggested_alternative", ""),
                savings_estimate=round(float(swap.get("savings_estimate", 0)), 2),
                rationale=swap.get("rationale", "")
            ))

        return BudgetBreakdown(
            categories=categories,
            grand_total=round(grand_total, 2),
            currency=constraints.currency,
            within_budget=within_budget,
            remaining_buffer=round(max(0, constraints.budget_total - grand_total), 2),
            violations=violations,
            suggested_swaps=suggested_swaps
        )

    async def _fallback_analyze(self, constraints: TravelConstraints) -> BudgetBreakdown:
        """Deterministic budget allocation when LLM is unavailable (0% drift)."""
        total = constraints.budget_total if constraints.budget_total > 0 else 1000.0
        cities_str = ", ".join(constraints.cities) if constraints.cities else (constraints.destination_region or "Destination")

        stay_cost = round(total * 0.35, 2)
        transport_cost = round(total * 0.20, 2)
        food_cost = round(total * 0.25, 2)
        activity_cost = round(total * 0.15, 2)
        buffer_cost = round(total - (stay_cost + transport_cost + food_cost + activity_cost), 2)

        categories = [
            BudgetCategory(
                category="stay",
                estimated_total=stay_cost,
                currency=constraints.currency,
                notes=f"Accommodations across {cities_str}"
            ),
            BudgetCategory(
                category="transport",
                estimated_total=transport_cost,
                currency=constraints.currency,
                notes="Intercity transit and local transport"
            ),
            BudgetCategory(
                category="food",
                estimated_total=food_cost,
                currency=constraints.currency,
                notes=f"Daily dining and meals ({constraints.duration_days} days)"
            ),
            BudgetCategory(
                category="activities",
                estimated_total=activity_cost,
                currency=constraints.currency,
                notes="Tours, admission tickets, and experiences"
            ),
            BudgetCategory(
                category="buffer",
                estimated_total=buffer_cost,
                currency=constraints.currency,
                notes="Contingency buffer and emergency reserve"
            ),
        ]

        grand_total = round(sum(c.estimated_total for c in categories), 2)
        within_budget = grand_total <= constraints.budget_total

        return BudgetBreakdown(
            categories=categories,
            grand_total=grand_total,
            currency=constraints.currency,
            within_budget=within_budget,
            remaining_buffer=round(max(0.0, constraints.budget_total - grand_total), 2),
            violations=[],
            suggested_swaps=[]
        )
