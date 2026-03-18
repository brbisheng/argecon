"""Economics-oriented rules and calculations."""

from .constraint_rules import detect_constraint_labels
from .demand_classifier import classify_demand_scenario
from .simple_calculator import calculate_simple_metrics

__all__ = [
    "calculate_simple_metrics",
    "classify_demand_scenario",
    "detect_constraint_labels",
]
