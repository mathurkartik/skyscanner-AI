"""
Destination Research Agent - Phase 4a.
Finds best places, experiences, and food based on traveler preferences.
Uses LLM to generate specific, real activities for any destination worldwide.
"""

from typing import List, Optional, Dict
import json
import logging
import re

from ..models import (
    TravelConstraints, ActivityCatalog, Activity, ActivityType,
    CrowdLevel, CostBand, PlaceInfo
)
from ..tools.google_places_client import get_google_places_client
from ..llm.llm_utils import validate_llm_json, validate_item_fields, extract_json_from_text

logger = logging.getLogger(__name__)


def _matches_place_name(act_name: str, place_name: str) -> bool:
    """Word-boundary aware matching to prevent false positives like 'Art' matching 'Kart racing' (AG-042)."""
    if not act_name or not place_name:
        return False
    a_lower = act_name.lower().strip()
    p_lower = place_name.lower().strip()
    if a_lower == p_lower:
        return True

    # Word-boundary check: exact phrase contained
    if re.search(rf"\b{re.escape(p_lower)}\b", a_lower) or re.search(rf"\b{re.escape(a_lower)}\b", p_lower):
        return True

    # Meaningful keyword overlap (tokens >= 4 chars, excluding generic travel words)
    stop = {"tour", "visit", "trip", "place", "city", "main", "hall", "street", "park", "hotel", "center"}
    a_words = {w for w in re.findall(r'\b[a-z]{4,}\b', a_lower) if w not in stop}
    p_words = {w for w in re.findall(r'\b[a-z]{4,}\b', p_lower) if w not in stop}
    overlap = a_words.intersection(p_words)
    if len(overlap) >= 2 or (overlap and (len(overlap) / max(len(a_words), len(p_words), 1)) >= 0.65):
        return True
    return False


class DestinationAgent:
    """
    Researches destinations and curates activity catalogs.
    Uses LLM knowledge to generate real, specific activities for any city,
    and Google Places client to enrich with ratings, reviews, photos, and opening hours.
    """

    def __init__(self, tool_router=None, llm_client=None, places_client=None):
        self.tool_router = tool_router
        self.llm_client = llm_client
        self.places_client = places_client or get_google_places_client()

    async def research(self, constraints: TravelConstraints) -> ActivityCatalog:
        """Generate ActivityCatalog from constraints using LLM and Google Places enrichment."""
        per_city_catalogs: Dict[str, List[str]] = {}
        all_activities: List[Activity] = []
        places_by_city: Dict[str, List[PlaceInfo]] = {}

        for city in constraints.cities:
            # 1. Fetch real Google Places POIs for this city
            try:
                real_places = await self.places_client.search_text(
                    query=f"top sights and attractions in {city}",
                    limit=8
                )
                places_by_city[city] = real_places
            except Exception as e:
                print(f"Google Places lookup failed for {city}: {e}")
                places_by_city[city] = []

            # 2. Generate activities via LLM
            city_activities = await self._research_city(city=city, constraints=constraints)

            # 3. Enrich activities with real Google Places details when names match (AG-042)
            if places_by_city[city]:
                for act in city_activities:
                    for p in places_by_city[city]:
                        if _matches_place_name(act.name, p.name):
                            if p.rating:
                                act.rationale += f" ★ {p.rating} ({p.review_count:,} reviews)"
                            if p.opening_hours:
                                act.best_time = f"Hours: {p.opening_hours[0]}"
                            break

            per_city_catalogs[city] = [a.id for a in city_activities]
            all_activities.extend(city_activities)

        return ActivityCatalog(
            activities=all_activities,
            per_city=per_city_catalogs,
            neighborhood_notes=self._create_neighborhood_notes(all_activities),
            places_by_city=places_by_city
        )

    async def _research_city(self, city: str, constraints: TravelConstraints) -> List[Activity]:
        """Research activities for a specific city, LLM-first."""
        if self.llm_client:
            try:
                activities = await self._llm_generate_activities(city, constraints)
                if activities:
                    return activities
            except Exception as e:
                print(f"LLM activity generation failed for {city}: {e}")

        return self._generate_generic_activities(city, constraints)

    async def _llm_generate_activities(self, city: str, constraints: TravelConstraints) -> List[Activity]:
        """Use LLM to generate specific activity names with details."""
        days_in_city = max(2, constraints.duration_days // max(1, len(constraints.cities)))
        non_food_count = min(15, max(6, days_in_city * 3))
        food_count = min(10, max(4, days_in_city * 2))
        activity_count = non_food_count + food_count

        system_prompt = f"""You are an expert local guide for {city}. Generate exactly {activity_count} activities.

Respond ONLY with valid JSON: {{"activities": [...]}}

Each activity: {{"name": "Real place name", "description": "One evocative sentence", "type": "temple|food|museum|nature|shopping|entertainment|other", "cost_band": "budget|moderate|expensive", "estimated_cost_usd": number, "address": "Area/district"}}

Requirements:
- {non_food_count} non-food (museums, landmarks, churches, parks, viewpoints, neighborhoods)
- {food_count} food (restaurants, bistros, bakeries, cafes — each DIFFERENT)
- ONLY real specific names, no generic labels
- All names unique. Mix iconic spots and hidden gems
- For estimated_cost_usd, provide realistic 2026 pricing in USD (e.g., Louvre = 22, Seine cruise = 18, street food = 8, free park/viewpoint = 0)
- Consider travel dates/seasonality and suggest weather-appropriate experiences (e.g., outdoor hikes in good seasons, indoor galleries/baths when cold or rainy)"""

        user_prompt = f"""Generate {activity_count} unique activities for {days_in_city} days in {city}:
Likes: {', '.join(constraints.preferences) if constraints.preferences else 'sightseeing, food, culture'}
Avoid: {', '.join(constraints.avoidances) if constraints.avoidances else 'none'}
Budget: {constraints.budget_total} {constraints.currency}
Travel Dates / Season: {constraints.start_date or 'Optimal travel window'}"""

        content = await self.llm_client.chat_with_retry(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=3500
        )

        cleaned_json = extract_json_from_text(content)
        data = json.loads(cleaned_json)

        if isinstance(data, dict):
            if "activities" not in data:
                logger.warning(f"[DestinationAgent] Missing 'activities' key in LLM response: {list(data.keys())}")
            activities_data = data.get("activities", [])
        elif isinstance(data, list):
            activities_data = data
        else:
            logger.warning(f"[DestinationAgent] Unexpected LLM output type: {type(data).__name__}")
            activities_data = []

        type_mapping = {
            "temple": ActivityType.TEMPLE, "food": ActivityType.FOOD,
            "museum": ActivityType.MUSEUM, "nature": ActivityType.NATURE,
            "shopping": ActivityType.SHOPPING, "entertainment": ActivityType.ENTERTAINMENT,
            "transport": ActivityType.TRANSPORT, "other": ActivityType.OTHER
        }
        crowd_mapping = {"low": CrowdLevel.LOW, "medium": CrowdLevel.MEDIUM, "high": CrowdLevel.HIGH}
        cost_mapping = {
            "budget": CostBand.BUDGET, "moderate": CostBand.MODERATE,
            "expensive": CostBand.EXPENSIVE, "luxury": CostBand.LUXURY
        }

        activities = []
        for i, item in enumerate(activities_data):
            if not isinstance(item, dict):
                logger.warning(f"[DestinationAgent] Activity entry {i} is not a dictionary: {type(item).__name__}")
                continue
            if not item.get("name"):
                logger.warning(f"[DestinationAgent] Activity entry {i} missing 'name' field: {item}")
            name = str(item.get("name", ""))[:100]
            rationale = str(item.get("rationale", "") or item.get("description", "") or "Worth visiting")[:200]
            description = str(item.get("description", ""))[:300] if item.get("description") else None
            best_time = str(item.get("best_time", ""))[:50]
            address = str(item.get("address", ""))[:100]

            name_part = name.lower().replace(' ', '-').replace("'", '').replace('"', '').replace('(', '').replace(')', '').replace('&', 'and').replace(',', '')[:30]
            activity_id = f"{city.lower().replace(' ', '-')}-{name_part}-{i}"

            cost_val = item.get("estimated_cost_usd", item.get("estimated_cost"))
            try:
                estimated_cost = float(cost_val) if cost_val is not None else None
            except (ValueError, TypeError):
                estimated_cost = None

            activity = Activity(
                id=activity_id,
                name=name,
                city=city,
                type=type_mapping.get(item.get("type"), ActivityType.OTHER),
                estimated_duration_hours=max(0.5, float(item.get("estimated_duration_hours", 2.0))),
                cost_band=cost_mapping.get(item.get("cost_band"), CostBand.MODERATE),
                estimated_cost=estimated_cost,
                crowd_level=crowd_mapping.get(item.get("crowd_level"), CrowdLevel.MEDIUM),
                must_do=bool(item.get("must_do", False)),
                rationale=rationale,
                description=description,
                address=address,
                best_time=best_time,
                tags=item.get("tags", [])[:5]
            )
            activities.append(activity)

        if constraints.avoidances:
            activities = self._filter_avoidances(activities, constraints.avoidances)

        return activities

    def _generate_generic_activities(self, city: str, constraints: TravelConstraints) -> List[Activity]:
        """Minimal generic fallback when LLM is unavailable."""
        city_clean = city.lower().replace(' ', '-')

        activities = [
            Activity(id=f"{city_clean}-landmark-0", name=f"{city} Main Landmark", city=city,
                     type=ActivityType.OTHER, estimated_duration_hours=2.5, cost_band=CostBand.MODERATE,
                     crowd_level=CrowdLevel.HIGH, must_do=True,
                     rationale=f"Top-rated attraction in {city}", tags=["sightseeing", "iconic"],
                     address=f"Central {city}"),
            Activity(id=f"{city_clean}-food-1", name=f"{city} Local Food Experience", city=city,
                     type=ActivityType.FOOD, estimated_duration_hours=2.0, cost_band=CostBand.MODERATE,
                     crowd_level=CrowdLevel.MEDIUM, must_do=True,
                     rationale=f"Authentic local cuisine in {city}", tags=["food", "local"],
                     address=f"Old Town, {city}"),
            Activity(id=f"{city_clean}-culture-2", name=f"{city} Cultural Site", city=city,
                     type=ActivityType.MUSEUM, estimated_duration_hours=2.0, cost_band=CostBand.MODERATE,
                     crowd_level=CrowdLevel.MEDIUM, must_do=False,
                     rationale=f"Cultural heritage of {city}", tags=["culture", "history"],
                     address=f"Museum District, {city}"),
            Activity(id=f"{city_clean}-nature-3", name=f"{city} Park or Garden", city=city,
                     type=ActivityType.NATURE, estimated_duration_hours=1.5, cost_band=CostBand.BUDGET,
                     crowd_level=CrowdLevel.LOW, must_do=False,
                     rationale=f"Green space in {city}", tags=["nature", "relaxing"],
                     address=f"City Park, {city}"),
        ]

        if constraints.avoidances:
            activities = self._filter_avoidances(activities, constraints.avoidances)

        return activities

    def _filter_avoidances(self, activities: List[Activity], avoidances: List[str]) -> List[Activity]:
        """Filter out activities matching avoidances across tags, names, descriptions, and rationales (AG-043)."""
        filtered = []
        avoidance_synonyms = {
            "alcohol": ["wine", "beer", "brewery", "distillery", "pub", "bar", "cocktail", "liquor", "vineyard"],
            "meat": ["steak", "beef", "pork", "barbecue", "bbq", "butcher", "bacon"],
            "smoking": ["cigar", "hookah", "tobacco", "shisha"],
        }

        for activity in activities:
            should_include = True
            act_text = f"{activity.name} {activity.description or ''} {activity.rationale or ''}".lower()

            for avoidance in avoidances:
                avoidance_lower = avoidance.lower().strip()
                if not avoidance_lower:
                    continue

                # 1. Tag matches
                if any(avoidance_lower in tag.lower() for tag in activity.tags):
                    should_include = False
                    break

                # 2. Crowd avoidance
                if avoidance_lower in ["crowd", "crowds"] and activity.crowd_level == CrowdLevel.HIGH:
                    should_include = False
                    break

                # 3. Direct word-boundary match in name, description, or rationale (AG-043)
                if re.search(rf"\b{re.escape(avoidance_lower)}\b", act_text):
                    should_include = False
                    break

                # 4. Synonym match (e.g. alcohol -> wine, bar, brewery)
                if avoidance_lower in avoidance_synonyms:
                    if any(re.search(rf"\b{re.escape(syn)}\b", act_text) for syn in avoidance_synonyms[avoidance_lower]):
                        should_include = False
                        break

            if should_include:
                filtered.append(activity)
        return filtered

    def _create_neighborhood_notes(self, activities: List[Activity]) -> Dict[str, str]:
        """Create neighborhood notes from activity addresses."""
        notes = {}
        for activity in activities:
            if activity.address:
                parts = activity.address.split(",")
                if len(parts) >= 2:
                    ward = parts[-2].strip() if len(parts) > 2 else parts[-1].strip()
                    if ward not in notes:
                        notes[ward] = f"Area with {activity.type.value} attractions"
        return notes
