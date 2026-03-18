"""Unified entrypoint that turns evidence and chunk metadata into extracted parameters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.common.schemas import ExtractedParameters
from src.econ.constraint_rules import detect_constraint_labels
from src.econ.demand_classifier import classify_demand_scenario
from src.econ.simple_calculator import calculate_simple_metrics
from src.extract.regex_extractors import extract_first_pass_slots


def _merge_target_texts(evidence_text: str, chunk_metadata: Mapping[str, Any] | None) -> str:
    parts = [evidence_text]
    if chunk_metadata:
        for key in ("section_title", "source_title", "chunk_text", "title"):
            value = chunk_metadata.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
        metadata = chunk_metadata.get("metadata")
        if isinstance(metadata, Mapping):
            for value in metadata.values():
                if isinstance(value, str) and value.strip():
                    parts.append(value.strip())
    return "\n".join(parts)


def parse_extracted_parameters(
    evidence_text: str,
    chunk_metadata: Mapping[str, Any] | None = None,
) -> ExtractedParameters:
    """Parse a single evidence span plus chunk metadata into structured parameters."""

    slots = extract_first_pass_slots(evidence_text, chunk_metadata)
    combined_text = _merge_target_texts(evidence_text, chunk_metadata)
    demand_scenario = classify_demand_scenario(combined_text)

    extracted = ExtractedParameters(
        demand_scenario=demand_scenario,
        loan_amount_upper_limit=slots["loan_amount_upper_limit"],
        loan_term_months=slots["loan_term_months"],
        interest_rate=slots["interest_rate"],
        subsidy_rate=slots["subsidy_rate"],
        collateral_required=slots["collateral_required"],
        collateral_requirement_text=slots["collateral_requirement_text"],
        guarantee_required=slots["guarantee_required"],
        guarantee_requirement_text=slots["guarantee_requirement_text"],
        target_entities=slots["target_entities"],
        usage_restrictions=slots["usage_restrictions"],
        repayment_constraints=slots["repayment_constraints"],
    )

    extracted.constraint_labels = detect_constraint_labels(combined_text, extracted)

    calculations = calculate_simple_metrics(extracted)
    extracted.effective_rate = calculations.get("effective_rate")
    extracted.raw_slots = {
        "evidence_text": evidence_text,
        "chunk_metadata": dict(chunk_metadata or {}),
        "regex_matches": slots,
        "calculations": calculations,
    }
    return extracted


__all__ = ["parse_extracted_parameters"]
