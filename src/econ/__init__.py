"""Economics-oriented rules and calculations."""

from .econ_adapter import adapt_econ_result
from .constraint_rules import detect_constraint_labels
from .demand_classifier import classify_demand_scenario
from .simple_calculator import calculate_simple_metrics

__all__ = [
    "adapt_econ_result",
    "calculate_simple_metrics",
    "classify_demand_scenario",
    "detect_constraint_labels",
]
