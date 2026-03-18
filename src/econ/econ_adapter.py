"""Deterministic economics adapter built on top of explicitly extracted parameters."""

from __future__ import annotations

from src.common import EconResult, ExtractedParameters
from src.common.enums import DemandScenario


def adapt_econ_result(extracted_parameters: ExtractedParameters | None) -> EconResult | None:
    """Convert extracted parameters into a conservative economics interpretation."""

    if extracted_parameters is None or not _has_explicit_signal(extracted_parameters):
        return None

    reasoning_steps: list[str] = []
    suggested_actions: list[str] = []
    conclusion_parts: list[str] = []

    if extracted_parameters.demand_scenario != DemandScenario.UNKNOWN:
        conclusion_parts.append(f"该需求更接近“{extracted_parameters.demand_scenario.value}”场景")
        reasoning_steps.append("需求场景来自证据句及上下文中的显式关键词")

    if extracted_parameters.loan_amount_upper_limit is not None:
        conclusion_parts.append(f"政策明确了额度上限 {extracted_parameters.loan_amount_upper_limit}")
        reasoning_steps.append("贷款额度上限来自证据中的显式数值")
    if extracted_parameters.loan_term_months is not None:
        conclusion_parts.append(f"政策明确了期限 {extracted_parameters.loan_term_months} 个月")
        reasoning_steps.append("贷款期限来自证据中的显式期限表述")

    if extracted_parameters.interest_rate is not None:
        conclusion_parts.append(f"名义利率约为 {extracted_parameters.interest_rate}")
        reasoning_steps.append("名义利率来自证据中的显式利率字段")
    if extracted_parameters.subsidy_rate is not None:
        conclusion_parts.append(f"贴息/补贴利率约为 {extracted_parameters.subsidy_rate}")
        reasoning_steps.append("贴息/补贴利率来自证据中的显式补贴字段")
    if extracted_parameters.effective_rate is not None:
        conclusion_parts.append(f"按显式参数计算的有效利率约为 {extracted_parameters.effective_rate}")
        reasoning_steps.append("有效利率按名义利率减去贴息/补贴利率直接计算")

    if extracted_parameters.collateral_required is True:
        conclusion_parts.append("该政策存在抵押要求")
        suggested_actions.append("提前核对可用于抵押的资产材料")
    elif extracted_parameters.collateral_required is False:
        conclusion_parts.append("证据未显示必须提供抵押")

    if extracted_parameters.guarantee_required is True:
        conclusion_parts.append("该政策存在担保要求")
        suggested_actions.append("确认担保人或保证方式是否满足要求")
    elif extracted_parameters.guarantee_required is False:
        conclusion_parts.append("证据未显示必须提供担保")

    if extracted_parameters.target_entities:
        conclusion_parts.append(f"适用主体包括 {'、'.join(extracted_parameters.target_entities)}")
    else:
        suggested_actions.append("补充主体类型以确认是否属于适用对象")

    if extracted_parameters.usage_restrictions:
        suggested_actions.append("核对贷款用途是否落在政策允许范围内")
    if extracted_parameters.repayment_constraints:
        suggested_actions.append("核对还款安排是否与政策要求一致")

    conclusion = "；".join(conclusion_parts) if conclusion_parts else "已抽取到部分政策参数，但不足以形成稳定的经济学解释。"
    confidence = _estimate_confidence(extracted_parameters)

    return EconResult(
        conclusion=conclusion,
        confidence=confidence,
        demand_scenario=extracted_parameters.demand_scenario,
        constraint_labels=list(extracted_parameters.constraint_labels),
        estimated_cost=extracted_parameters.effective_rate,
        suggested_actions=_dedupe_preserve_order(suggested_actions),
        reasoning_steps=_dedupe_preserve_order(reasoning_steps),
        metadata={"derived_from_explicit_parameters": True},
    )


def _has_explicit_signal(extracted_parameters: ExtractedParameters) -> bool:
    return any(
        value not in (None, [], "")
        for value in (
            extracted_parameters.loan_amount_upper_limit,
            extracted_parameters.loan_term_months,
            extracted_parameters.interest_rate,
            extracted_parameters.subsidy_rate,
            extracted_parameters.effective_rate,
            extracted_parameters.collateral_required,
            extracted_parameters.guarantee_required,
            extracted_parameters.target_entities,
            extracted_parameters.usage_restrictions,
            extracted_parameters.repayment_constraints,
            extracted_parameters.constraint_labels,
        )
    ) or extracted_parameters.demand_scenario != DemandScenario.UNKNOWN


def _estimate_confidence(extracted_parameters: ExtractedParameters) -> float:
    score = 0.45
    if extracted_parameters.demand_scenario != DemandScenario.UNKNOWN:
        score += 0.1
    if extracted_parameters.loan_amount_upper_limit is not None:
        score += 0.1
    if extracted_parameters.loan_term_months is not None:
        score += 0.1
    if extracted_parameters.interest_rate is not None:
        score += 0.1
    if extracted_parameters.subsidy_rate is not None:
        score += 0.1
    if extracted_parameters.effective_rate is not None:
        score += 0.1
    return min(score, 0.95)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


__all__ = ["adapt_econ_result"]
