"""
Trip Structuring Agent — Hierarchical planning layer.
Converts TravelConstraints into structured regions and route plan
BEFORE the parallel worker agents execute.

Uses LLM to generate region breakdowns for ANY destination,
instead of relying on hardcoded route databases.
"""

import json
from typing import List, Optional
from ..models.schemas import TravelConstraints, TripStructure, Region


class TripStructuringAgent:
    """
    Creates trip structure BEFORE parallel execution.
    Divides trips into logical regions with day allocations.
    Uses LLM knowledge to generate regions for any destination worldwide.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def structure(self, constraints: TravelConstraints) -> TripStructure:
        """
        Convert TravelConstraints into a TripStructure with regions.

        Rules:
        - duration > 7 days → MUST create multiple regions
        - road trip → generate a driving route with ordered stops
        - Total allocated days MUST equal duration_days
        """
        duration = constraints.duration_days

        if duration <= 7 and len(constraints.cities) <= 2 and not constraints.is_road_trip:
            return self._structure_city_trip(constraints)

        if self.llm_client:
            try:
                return await self._llm_generate_structure(constraints)
            except Exception as e:
                print(f"LLM trip structuring failed: {e}")

        return self._structure_from_cities(constraints)

    async def _llm_generate_structure(self, constraints: TravelConstraints) -> TripStructure:
        """Use LLM to generate a region-based trip structure for any destination."""
        trip_type = "road_trip" if constraints.is_road_trip else "multi_region"

        system_prompt = f"""You are a travel route planner. Generate a trip structure for a {constraints.duration_days}-day {"road trip" if constraints.is_road_trip else "trip"} to {constraints.destination_region}.

Respond with valid JSON:
{{
  "trip_type": "{trip_type}",
  "regions": [
    {{
      "name": "Region or area name",
      "base_location": "Main city or town to stay",
      "days": number of days to spend,
      "highlights": ["3-5 specific must-see attractions or experiences"]
    }}
  ],
  "route": ["ordered list of stops/cities"],
  "pace": "relaxed" or "balanced" or "aggressive"
}}

Rules:
- Total days across all regions MUST equal exactly {constraints.duration_days}
- Each region gets at least 1 day
- Use REAL place names, not generic labels
- Order regions geographically to minimize backtracking
- {"Plan as a driving route with logical road connections" if constraints.is_road_trip else "Plan as a multi-city itinerary with logical travel connections"}
- Include the user's specified cities: {', '.join(constraints.cities)}
- Highlights should be specific landmarks, not generic descriptions"""

        user_prompt = f"""Plan a {constraints.duration_days}-day {"road trip" if constraints.is_road_trip else "trip"} to {constraints.destination_region}.
Cities to include: {', '.join(constraints.cities)}
Preferences: {', '.join(constraints.preferences) if constraints.preferences else 'general sightseeing'}
Budget level: {constraints.budget_total} {constraints.currency}"""

        content = await self.llm_client.chat_with_retry(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=2000
        )

        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:])
            if "```" in content:
                content = content[:content.rfind("```")]
        brace = content.find("{")
        if brace > 0:
            content = content[brace:]
        data = json.loads(content)

        regions = []
        for r in data.get("regions", []):
            regions.append(Region(
                name=r["name"],
                base_location=r["base_location"],
                days=r["days"],
                highlights=r.get("highlights", [])[:5]
            ))

        total_days = sum(r.days for r in regions)
        if total_days != constraints.duration_days:
            regions = self._adjust_days_to_match(regions, constraints.duration_days)

        return TripStructure(
            trip_type=data.get("trip_type", trip_type),
            regions=regions,
            route=data.get("route", [r.base_location for r in regions]),
            pace=data.get("pace", self._determine_pace(constraints.duration_days, len(regions)))
        )

    def _adjust_days_to_match(self, regions: List[Region], target: int) -> List[Region]:
        """Ensure total allocated days equals the target duration."""
        if not regions:
            return regions

        total = sum(r.days for r in regions)
        adjusted = [r.model_copy() for r in regions]

        while total != target:
            if total < target:
                largest_idx = max(range(len(adjusted)), key=lambda i: adjusted[i].days)
                adjusted[largest_idx] = Region(
                    name=adjusted[largest_idx].name,
                    base_location=adjusted[largest_idx].base_location,
                    days=adjusted[largest_idx].days + 1,
                    highlights=adjusted[largest_idx].highlights.copy()
                )
                total += 1
            else:
                candidates = [i for i, r in enumerate(adjusted) if r.days > 1]
                if not candidates:
                    break
                largest_idx = max(candidates, key=lambda i: adjusted[i].days)
                adjusted[largest_idx] = Region(
                    name=adjusted[largest_idx].name,
                    base_location=adjusted[largest_idx].base_location,
                    days=adjusted[largest_idx].days - 1,
                    highlights=adjusted[largest_idx].highlights.copy()
                )
                total -= 1

        return adjusted

    def _structure_city_trip(self, constraints: TravelConstraints) -> TripStructure:
        """Structure a simple city trip (≤ 7 days, 1-2 cities)."""
        regions = []
        days_per_city = max(1, constraints.duration_days // len(constraints.cities))
        remainder = constraints.duration_days % len(constraints.cities)

        for i, city in enumerate(constraints.cities):
            extra = 1 if i < remainder else 0
            regions.append(Region(
                name=city,
                base_location=city,
                days=days_per_city + extra,
                highlights=[]
            ))

        return TripStructure(
            trip_type="city_trip",
            regions=regions,
            route=constraints.cities,
            pace="relaxed" if constraints.duration_days >= 5 else "balanced"
        )

    def _structure_from_cities(self, constraints: TravelConstraints) -> TripStructure:
        """Fallback: structure from the cities list when LLM is unavailable."""
        cities = constraints.cities
        duration = constraints.duration_days

        if len(cities) == 1:
            city = cities[0]
            if duration <= 3:
                regions = [Region(name=city, base_location=city, days=duration, highlights=[])]
            else:
                half = duration // 2
                regions = [
                    Region(name=f"{city} Central", base_location=city, days=half, highlights=[]),
                    Region(name=f"{city} Surroundings", base_location=city, days=duration - half, highlights=[]),
                ]
        else:
            days_per = max(1, duration // len(cities))
            remainder = duration % len(cities)
            regions = []
            for i, city in enumerate(cities):
                extra = 1 if i < remainder else 0
                regions.append(Region(
                    name=city,
                    base_location=city,
                    days=days_per + extra,
                    highlights=[]
                ))

        return TripStructure(
            trip_type="multi_region" if len(regions) > 1 else "city_trip",
            regions=regions,
            route=[r.base_location for r in regions],
            pace=self._determine_pace(duration, len(regions))
        )

    def _determine_pace(self, duration: int, num_regions: int) -> str:
        if num_regions == 0:
            return "balanced"
        ratio = duration / num_regions
        if ratio >= 3:
            return "relaxed"
        elif ratio >= 2:
            return "balanced"
        else:
            return "aggressive"
