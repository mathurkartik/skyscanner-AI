"""Pydantic models for agent communication."""

from .schemas import (
    # Core constraints
    TravelConstraints,
    Region,
    TripStructure,
    
    # Destination outputs
    Activity,
    ActivityType,
    ActivityCatalog,
    CrowdLevel,
    CostBand,
    
    # Logistics outputs
    LodgingPlan,
    MovementPlan,
    DaySlot,
    DaySkeleton,
    LogisticsOutput,
    
    # Budget outputs
    BudgetCategory,
    BudgetViolation,
    SuggestedSwap,
    BudgetBreakdown,
    
    # Merge outputs
    DayItineraryItem,
    DayItinerary,
    DraftItinerary,
    
    # Review outputs
    ChecklistItem,
    RepairHint,
    ReviewReport,
    ReviewSeverity,
    ReviewStatus,
    
    # Final output
    ExperienceHighlight,
    FinalItinerary,
    PlanInsights,
    
    # API models
    PlanRequest,
    PlanResponse,
    HealthResponse,
    RealFlightOffer,
    TransportSegment,
    RealHotelOffer,
    PlaceInfo,
    CarEstimate,
    MapPin,
    CostSavingTip,
    PracticalInfo,
    
    # Test fixtures
    JAPAN_5D_TOKYO_KYOTO_3000_CONSTRAINTS,
)

from .exceptions import (
    MissingConstraintError,
    InvalidConstraintError,
)

__all__ = [
    "TravelConstraints",
    "Region",
    "TripStructure",
    "Activity",
    "ActivityType",
    "ActivityCatalog",
    "CrowdLevel",
    "CostBand",
    "LodgingPlan",
    "MovementPlan",
    "DaySlot",
    "DaySkeleton",
    "LogisticsOutput",
    "BudgetCategory",
    "BudgetViolation",
    "SuggestedSwap",
    "BudgetBreakdown",
    "DayItineraryItem",
    "DayItinerary",
    "DraftItinerary",
    "ChecklistItem",
    "RepairHint",
    "ReviewReport",
    "ReviewSeverity",
    "ReviewStatus",
    "ExperienceHighlight",
    "FinalItinerary",
    "PlanInsights",
    "PlanRequest",
    "PlanResponse",
    "HealthResponse",
    "RealFlightOffer",
    "TransportSegment",
    "RealHotelOffer",
    "PlaceInfo",
    "CarEstimate",
    "MapPin",
    "CostSavingTip",
    "PracticalInfo",
    "MissingConstraintError",
    "InvalidConstraintError",
    "JAPAN_5D_TOKYO_KYOTO_3000_CONSTRAINTS",
]

