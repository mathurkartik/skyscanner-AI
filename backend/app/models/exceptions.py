"""
Domain exceptions for travel planning constraint validation.
"""

from typing import List, Optional


class MissingConstraintError(ValueError):
    """
    Raised when one or more essential constraints (Destination, Duration, Budget)
    are missing from the user's travel request.
    """
    def __init__(
        self,
        missing_fields: List[str],
        message: Optional[str] = None,
        suggested_tiers: Optional[List[dict]] = None
    ):
        self.missing_fields = missing_fields
        self.suggested_tiers = suggested_tiers or [
            {"tier": "budget", "label": "Budget / Backpacker (~$70/day)"},
            {"tier": "moderate", "label": "Moderate / Comfortable (~$180/day)"},
            {"tier": "luxury", "label": "Luxury / Premium (~$400+/day)"},
        ]
        
        if not message:
            field_names = []
            for f in missing_fields:
                if f == "destination":
                    field_names.append("Destination (e.g., Tokyo, Paris)")
                elif f == "duration":
                    field_names.append("Duration (e.g., 5 days)")
                elif f == "budget":
                    field_names.append("Budget (e.g., $2,000 or Moderate)")
                else:
                    field_names.append(f.capitalize())
            
            message = (
                f"Please provide the missing details: {', '.join(field_names)}."
            )
            
        self.message = message
        super().__init__(message)


class InvalidConstraintError(ValueError):
    """Raised when an extracted constraint violates domain requirements."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Invalid {field}: {message}")
