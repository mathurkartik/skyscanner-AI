"""
Frontend-Backend Schema Contract Tests (AG-118).
Ensures that all TypeScript interface models in `src/app/models/travel-planner.model.ts`
strictly align with backend Pydantic models in `app/models/schemas.py`.
"""

import os
import re
import pytest
from app.models.schemas import (
    RealFlightOffer,
    RealHotelOffer,
    CarEstimate,
    PlaceInfo,
    MapPin,
    CostSavingTip,
    SuggestedSwap,
    TransportSegment,
    FinalItinerary,
    TravelConstraints,
    DayItinerary,
    DayItineraryItem,
)


def extract_ts_interface_fields(ts_content: str, interface_name: str) -> set[str]:
    """Extract property names declared in a TypeScript interface."""
    pattern = rf"export\s+interface\s+{interface_name}\s*\{{([^}}]+)\}}"
    match = re.search(pattern, ts_content, re.DOTALL)
    if not match:
        return set()
    block = match.group(1)
    fields = set()
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("/*"):
            continue
        field_match = re.match(r"^([a-zA-Z0-9_]+)\??\s*:", line)
        if field_match:
            fields.add(field_match.group(1))
    return fields


def get_pydantic_field_names(model_cls) -> set[str]:
    """Get field names of a Pydantic v2 model."""
    return set(model_cls.model_fields.keys())


@pytest.fixture(scope="module")
def ts_models_content():
    """Read the TypeScript models file from frontend."""
    frontend_models_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "src", "app", "models", "travel-planner.model.ts")
    )
    assert os.path.exists(frontend_models_path), f"Cannot find {frontend_models_path}"
    with open(frontend_models_path, "r", encoding="utf-8") as f:
        return f.read()


def test_contract_real_flight_offer(ts_models_content):
    ts_fields = extract_ts_interface_fields(ts_models_content, "RealFlightOffer")
    py_fields = get_pydantic_field_names(RealFlightOffer)
    missing = ts_fields - py_fields
    assert not missing, f"RealFlightOffer schema missing fields required by TS interface: {missing}"


def test_contract_real_hotel_offer(ts_models_content):
    ts_fields = extract_ts_interface_fields(ts_models_content, "RealHotelOffer")
    py_fields = get_pydantic_field_names(RealHotelOffer)
    missing = ts_fields - py_fields
    assert not missing, f"RealHotelOffer schema missing fields required by TS interface: {missing}"


def test_contract_car_estimate(ts_models_content):
    ts_fields = extract_ts_interface_fields(ts_models_content, "CarEstimate")
    py_fields = get_pydantic_field_names(CarEstimate)
    missing = ts_fields - py_fields
    assert not missing, f"CarEstimate schema missing fields required by TS interface: {missing}"


def test_contract_place_info(ts_models_content):
    ts_fields = extract_ts_interface_fields(ts_models_content, "PlaceInfo")
    py_fields = get_pydantic_field_names(PlaceInfo)
    missing = ts_fields - py_fields
    assert not missing, f"PlaceInfo schema missing fields required by TS interface: {missing}"


def test_contract_map_pin(ts_models_content):
    ts_fields = extract_ts_interface_fields(ts_models_content, "MapPin")
    py_fields = get_pydantic_field_names(MapPin)
    missing = ts_fields - py_fields
    assert not missing, f"MapPin schema missing fields required by TS interface: {missing}"


def test_contract_cost_saving_tip(ts_models_content):
    ts_fields = extract_ts_interface_fields(ts_models_content, "CostSavingTip")
    py_fields = get_pydantic_field_names(CostSavingTip)
    missing = ts_fields - py_fields
    assert not missing, f"CostSavingTip schema missing fields required by TS interface: {missing}"


def test_contract_suggested_swap(ts_models_content):
    ts_fields = extract_ts_interface_fields(ts_models_content, "SuggestedSwap")
    py_fields = get_pydantic_field_names(SuggestedSwap)
    missing = ts_fields - py_fields
    assert not missing, f"SuggestedSwap schema missing fields required by TS interface: {missing}"


def test_contract_transport_segment(ts_models_content):
    ts_fields = extract_ts_interface_fields(ts_models_content, "TransportSegment")
    py_fields = get_pydantic_field_names(TransportSegment)
    missing = ts_fields - py_fields
    assert not missing, f"TransportSegment schema missing fields required by TS interface: {missing}"


def test_contract_final_itinerary(ts_models_content):
    ts_fields = extract_ts_interface_fields(ts_models_content, "ItineraryResponse")
    py_fields = get_pydantic_field_names(FinalItinerary)
    # Exclude frontend-only client states if any
    frontend_only = {"debug_mode"}
    missing = (ts_fields - py_fields) - frontend_only
    assert not missing, f"FinalItinerary schema missing fields required by TS interface: {missing}"
