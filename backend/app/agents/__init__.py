"""
Multi-Agent System - Specialized agents for travel planning.

Agents:
- Orchestrator: Constraint extraction, task dispatch, merge, repair loop
- Destination: Activity catalog generation
- Logistics: Lodging and transport planning
- Budget: Cost analysis and budget management
- Review: Quality gate validation
"""

from .orchestrator import OrchestratorAgent
from .destination import DestinationAgent
from .logistics import LogisticsAgent
from .budget import BudgetAgent
from .review import ReviewAgent
from .trip_structuring import TripStructuringAgent

__all__ = [
    "OrchestratorAgent",
    "DestinationAgent",
    "LogisticsAgent",
    "BudgetAgent",
    "ReviewAgent",
    "TripStructuringAgent",
]
