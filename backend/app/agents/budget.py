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
        """Enrich and calibrate budget categories with actual flight and hotel quotes."""
        fx_usd_to_curr = 83.0 if constraints.currency == "INR" else (0.92 if constraints.currency == "EUR" else 1.0)
        
        # 1. Calibrate Flights / Transport
        flight_cost_curr = 0.0
        if logistics_output.flight_offers:
            cheapest_flight = min(logistics_output.flight_offers, key=lambda f: f.price)
            flight_cost_curr = round(cheapest_flight.price * fx_usd_to_curr, 2)

        # 2. Calibrate Hotel Stay
        hotel_total_curr = 0.0
        hotel_swaps: List[SuggestedSwap] = []
        for city, hotels in logistics_output.hotels_by_city.items():
            if hotels:
                selected_hotel = hotels[0]
                hotel_total_curr += round(selected_hotel.total_price * fx_usd_to_curr, 2)
                # If cheaper alternatives exist, create swap
                if len(hotels) > 1:
                    cheapest_hotel = min(hotels, key=lambda h: h.price_per_night)
                    comparison_hotel = selected_hotel if cheapest_hotel.name != selected_hotel.name else max(hotels, key=lambda h: h.price_per_night)
                    if cheapest_hotel.name != comparison_hotel.name and comparison_hotel.price_per_night > cheapest_hotel.price_per_night:
                        savings = round((comparison_hotel.price_per_night - cheapest_hotel.price_per_night) * fx_usd_to_curr, 2)
                        hotel_swaps.append(SuggestedSwap(
                            original_item=f"Stay at {comparison_hotel.name} ({city})",
                            suggested_alternative=f"Switch to {cheapest_hotel.name} ({city})",
                            savings_estimate=savings,
                            rationale=f"Save {savings} {constraints.currency}/night with high guest rating ({cheapest_hotel.guest_rating}★)"
                        ))

        # Update or populate categories so rollup is always complete
        cat_map = {c.category: c for c in breakdown.categories}
        
        if hotel_total_curr > 0:
            cat_map["stay"] = BudgetCategory(
                category="stay",
                estimated_total=hotel_total_curr,
                currency=constraints.currency,
                notes="Real rates from Booking.com inventory"
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
                notes="Real flight quotes from Skyscanner inventory"
            )
        elif "transport" not in cat_map:
            cat_map["transport"] = BudgetCategory(
                category="transport",
                estimated_total=round(constraints.budget_total * 0.20, 2),
                currency=constraints.currency,
                notes="Estimated intercity and local transit"
            )

        if "food" not in cat_map:
            cat_map["food"] = BudgetCategory(
                category="food",
                estimated_total=round(constraints.budget_total * 0.25, 2),
                currency=constraints.currency,
                notes="Estimated daily meals and dining"
            )

        if "activities" not in cat_map:
            cat_map["activities"] = BudgetCategory(
                category="activities",
                estimated_total=round(constraints.budget_total * 0.15, 2),
                currency=constraints.currency,
                notes="Estimated attraction tickets and tours"
            )

        # Standard category order
        order = ["stay", "transport", "food", "activities", "buffer"]
        updated_categories = [cat_map[k] for k in order if k in cat_map]
        for k, v in cat_map.items():
            if k not in order:
                updated_categories.append(v)

        grand_total = round(sum(c.estimated_total for c in updated_categories), 2)
        within_budget = grand_total <= constraints.budget_total
        violations = []
        if not within_budget:
            violations.append(BudgetViolation(
                category="total",
                estimated=grand_total,
                limit=constraints.budget_total,
                over_by=round(grand_total - constraints.budget_total, 2)
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

        categories = []
        for cat in data.get("categories", []):
            categories.append(BudgetCategory(
                category=cat["category"],
                estimated_total=round(float(cat["estimated_total"]), 2),
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
        """Simple fallback when LLM is unavailable."""
        categories = []
        total_cost = 0.0

        daily_budget = constraints.budget_total / max(1, constraints.duration_days)
        stay_pct, food_pct, transport_pct, activity_pct = 0.35, 0.25, 0.20, 0.20

        cities = constraints.cities if constraints.cities else [constraints.destination_region or "Destination"]
        for city in cities:
            days = max(1, constraints.duration_days // len(cities))
            city_budget = daily_budget * days

            stay_cost = round(city_budget * stay_pct, 2)
            food_cost = round(city_budget * food_pct, 2)
            transport_cost = round(city_budget * transport_pct, 2)
            activity_cost = round(city_budget * activity_pct, 2)

            categories.extend([
                BudgetCategory(category="stay", estimated_total=stay_cost,
                               currency=constraints.currency, notes=f"{days} nights in {city}"),
                BudgetCategory(category="food", estimated_total=food_cost,
                               currency=constraints.currency, notes=f"{days} days of meals in {city}"),
                BudgetCategory(category="transport", estimated_total=transport_cost,
                               currency=constraints.currency, notes=f"Local + inter-city transport from {city}"),
                BudgetCategory(category="activities", estimated_total=activity_cost,
                               currency=constraints.currency, notes=f"Activities and attractions in {city}"),
            ])
            total_cost += stay_cost + food_cost + transport_cost + activity_cost

        within_budget = total_cost <= constraints.budget_total
        violations = []
        if not within_budget:
            violations.append(BudgetViolation(
                category="total", estimated=total_cost,
                limit=constraints.budget_total, over_by=total_cost - constraints.budget_total
            ))

        return BudgetBreakdown(
            categories=categories,
            grand_total=round(total_cost, 2),
            currency=constraints.currency,
            within_budget=within_budget,
            remaining_buffer=round(max(0, constraints.budget_total - total_cost), 2),
            violations=violations,
            suggested_swaps=[]
        )
