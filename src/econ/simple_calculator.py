"""Simple deterministic calculations on explicitly extracted finance fields."""

from __future__ import annotations

from src.common.schemas import ExtractedParameters


def calculate_simple_metrics(parameters: ExtractedParameters) -> dict[str, float | None]:
    """Compute only directly supported metrics without guessing missing evidence."""

    effective_rate = None
    if parameters.interest_rate is not None and parameters.subsidy_rate is not None:
        effective_rate = parameters.interest_rate - parameters.subsidy_rate

    return {
        "effective_rate": effective_rate,
    }


__all__ = ["calculate_simple_metrics"]
