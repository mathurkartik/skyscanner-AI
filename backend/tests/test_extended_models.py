"""
Tests for Extended Data Models (Phase 4).
Verifies serialization/deserialization, default values, and schema compatibility
for CarEstimate, MapPin, CostSavingTip, extended DayItinerary, and FinalItinerary.
"""

from uuid import uuid4
import pytest
from app.models.schemas import (
    CarEstimate,
    MapPin,
    CostSavingTip,
    PlaceInfo,
    RealFlightOffer,
    RealHotelOffer,
    DayItinerary,
    DayItineraryItem,
    FinalItinerary,
    TravelConstraints,
    BudgetBreakdown,
    BudgetCategory,
    ReviewStatus,
    ActivityType,
)


def test_car_estimate_model():
    """Verify CarEstimate creation and default values."""
    car = CarEstimate(
        vehicle_name="Toyota RAV4 4WD",
        category="SUV",
        price_per_day=75.0,
        total_price=525.0,
        currency="USD",
        seats=5,
        transmission="Automatic"
    )

    assert car.is_estimate is True
    assert car.supplier == "Skyscanner Car Hire"
    assert car.price_per_day == 75.0
    assert car.id.startswith("car-")
    
    # Test JSON serialization
    data = car.model_dump()
    assert data["category"] == "SUV"
    assert data["total_price"] == 525.0


def test_map_pin_model():
    """Verify MapPin creation with different pin types."""
    pin = MapPin(
        label="Reynisfjara Black Sand Beach",
        lat=63.4044,
        lng=-19.0494,
        day_number=2,
        pin_type="attraction",
        description="Famous basalt columns"
    )

    assert pin.pin_type == "attraction"
    assert pin.lat == 63.4044
    assert pin.day_number == 2
    assert pin.id.startswith("pin-")


def test_cost_saving_tip_model():
    """Verify CostSavingTip creation."""
    tip = CostSavingTip(
        title="Buy Groceries at Bónus or Krónan",
        description="Dining out in Iceland is expensive. Buying breakfast and picnic supplies saves $30-50 per day.",
        estimated_savings="$250 - $350 total"
    )

    assert tip.title.startswith("Buy Groceries")
    assert tip.estimated_savings is not None
    assert tip.id.startswith("tip-")


def test_day_itinerary_extended_defaults():
    """Verify DayItinerary backward compatibility with empty defaults for new fields."""
    day = DayItinerary(
        day_number=1,
        city="Reykjavik",
        items=[
            DayItineraryItem(
                slot_index=0,
                time="09:00 - 11:00",
                activity_name="Hallgrímskirkja",
                city="Reykjavik",
                type=ActivityType.TEMPLE,
                cost_estimate=10.0,
            )
        ],
        day_summary="Explore central Reykjavik architecture.",
        day_cost=10.0
    )

    # Defaults must be empty lists / None
    assert day.hotel_options == []
    assert day.places == []
    assert day.driving_time_to_next is None


def test_day_itinerary_with_real_data():
    """Verify DayItinerary carrying hotel options and PlaceInfo."""
    hotel = RealHotelOffer(
        name="SM Hostel",
        city="Reykjavik",
        price_per_night=112.0,
        total_price=336.0,
        currency="USD",
        star_rating=3.0,
        guest_rating=8.4
    )

    place = PlaceInfo(
        name="Hallgrímskirkja",
        rating=4.6,
        review_count=18200,
        lat=64.1417,
        lng=-21.9266,
        city="Reykjavik"
    )

    day = DayItinerary(
        day_number=1,
        city="Reykjavik",
        items=[],
        day_summary="First day in Iceland.",
        day_cost=0.0,
        hotel_options=[hotel],
        places=[place],
        driving_time_to_next="2h 15m to Vík"
    )

    assert len(day.hotel_options) == 1
    assert day.hotel_options[0].name == "SM Hostel"
    assert len(day.places) == 1
    assert day.places[0].name == "Hallgrímskirkja"
    assert day.driving_time_to_next == "2h 15m to Vík"


def test_final_itinerary_extended_serialization():
    """Verify FinalItinerary with real flight offers, car estimates, and map pins."""
    constraints = TravelConstraints(
        destination_region="Iceland",
        cities=["Reykjavik", "Vík"],
        duration_days=5,
        budget_total=350000,
        currency="INR"
    )

    budget = BudgetBreakdown(
        categories=[
            BudgetCategory(category="transport", estimated_total=150000, currency="INR"),
            BudgetCategory(category="stay", estimated_total=100000, currency="INR"),
            BudgetCategory(category="food", estimated_total=50000, currency="INR"),
            BudgetCategory(category="activities", estimated_total=20000, currency="INR"),
        ],
        grand_total=320000,
        currency="INR",
        within_budget=True,
        remaining_buffer=30000,
    )

    flight = RealFlightOffer(
        airline="Air India / Lufthansa",
        airline_code="AI",
        origin="NAG",
        destination="KEF",
        price=1180.0,
        currency="USD",
        duration_minutes=960,
        stops=2,
        layover_airports=["DEL", "FRA"],
        departure="2026-12-01T08:30:00",
        arrival="2026-12-01T21:45:00"
    )

    car = CarEstimate(
        vehicle_name="Dacia Duster 4x4",
        category="SUV",
        price_per_day=80.0,
        total_price=400.0,
        currency="USD"
    )

    pin = MapPin(
        label="Reykjavik Base",
        lat=64.1466,
        lng=-21.9426,
        day_number=1,
        pin_type="overnight"
    )

    tip = CostSavingTip(
        title="Book Car with Gravel Protection",
        description="Icelandic rural roads often chip windshields. Full insurance avoids surprise $1000 fees."
    )

    itinerary = FinalItinerary(
        constraints=constraints,
        days=[],
        neighborhoods={"Reykjavik": ["Vesturbær", "Miðborg"]},
        logistics_summary="Fly into KEF, rent 4x4, drive south coast to Vík.",
        budget_rollup=budget,
        review_status=ReviewStatus.PASS,
        flight_options=[flight],
        car_estimates=[car],
        map_pins=[pin],
        cost_saving_tips_v2=[tip]
    )

    assert len(itinerary.flight_options) == 1
    assert itinerary.flight_options[0].origin == "NAG"
    assert len(itinerary.car_estimates) == 1
    assert itinerary.car_estimates[0].vehicle_name == "Dacia Duster 4x4"
    assert len(itinerary.map_pins) == 1
    assert itinerary.map_pins[0].pin_type == "overnight"
    assert len(itinerary.cost_saving_tips_v2) == 1

    # Roundtrip JSON test
    json_data = itinerary.model_dump_json()
    reloaded = FinalItinerary.model_validate_json(json_data)
    assert reloaded.flight_options[0].airline == "Air India / Lufthansa"
    assert reloaded.car_estimates[0].is_estimate is True
    assert reloaded.map_pins[0].lat == 64.1466
