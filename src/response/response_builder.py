"""Structured response assembly for evidence-grounded answers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from src.common import EconResult, ExtractedParameters, RetrievedChunk, SelectedEvidence, SessionState
from src.common.enums import DemandScenario
from src.evidence.confidence import assess_evidence_confidence
from src.response.templates import RESPONSE_TEMPLATES


_NUMERIC_PARAMETER_LABELS = {
    "loan_amount": "贷款金额",
    "loan_amount_upper_limit": "贷款额度上限",
    "loan_term_months": "贷款期限（月）",
    "interest_rate": "利率",
    "subsidy_rate": "贴息/补贴利率",
    "effective_rate": "有效利率",
}


_BOOL_PARAMETER_LABELS = {
    "collateral_required": "是否要求抵押",
    "guarantee_required": "是否要求担保",
}


_TEXT_PARAMETER_LABELS = {
    "collateral_requirement_text": "抵押要求说明",
    "guarantee_requirement_text": "担保要求说明",
}


_LIST_PARAMETER_LABELS = {
    "constraint_labels": "约束标签",
    "target_entities": "适用主体",
    "usage_restrictions": "用途限制",
    "repayment_constraints": "还款约束",
}


def build_structured_response(
    normalized_query: str,
    retrieved_chunks: Iterable[RetrievedChunk],
    selected_evidence: Iterable[SelectedEvidence],
    extracted_parameters: ExtractedParameters | None,
    econ_result: EconResult | None,
    session_state: SessionState,
) -> dict[str, Any]:
    """Assemble a structured, evidence-grounded response payload."""

    retrieved_chunk_list = list(retrieved_chunks)
    evidence_list = list(selected_evidence)
    confidence_assessment = assess_evidence_confidence(normalized_query, evidence_list)
    scenario = _detect_scenario(
        retrieved_chunk_list=retrieved_chunk_list,
        evidence_list=evidence_list,
        extracted_parameters=extracted_parameters,
        econ_result=econ_result,
        confidence_assessment=confidence_assessment,
    )

    citations = _build_citations(evidence_list, retrieved_chunk_list)
    summary = _build_summary(
        scenario=scenario,
        normalized_query=normalized_query,
        citations=citations,
        extracted_parameters=extracted_parameters,
        econ_result=econ_result,
        confidence_assessment=confidence_assessment,
    )
    uncertainty = _build_uncertainty(
        scenario=scenario,
        extracted_parameters=extracted_parameters,
        confidence_assessment=confidence_assessment,
        retrieved_chunk_list=retrieved_chunk_list,
        evidence_list=evidence_list,
    )
    final_response = _render_final_response(
        scenario=scenario,
        normalized_query=normalized_query,
        summary=summary,
        citations=citations,
        uncertainty=uncertainty,
        extracted_parameters=extracted_parameters,
        econ_result=econ_result,
    )

    return {
        "scenario": scenario,
        "summary": summary,
        "citations": citations,
        "uncertainty": uncertainty,
        "session_state": _serialize_session_state(session_state),
        "final_response": final_response,
        "trace": {
            "normalized_query": normalized_query,
            "retrieved_chunk_count": len(retrieved_chunk_list),
            "selected_evidence_count": len(evidence_list),
            "retrieved_chunks": [_serialize_retrieved_chunk(chunk) for chunk in retrieved_chunk_list],
            "selected_evidence": [_serialize_evidence(item) for item in evidence_list],
            "extracted_parameters": _serialize_extracted_parameters(extracted_parameters),
            "econ_result": _serialize_econ_result(econ_result),
            "session_state": _serialize_session_state(session_state),
        },
    }


def _detect_scenario(
    *,
    retrieved_chunk_list: list[RetrievedChunk],
    evidence_list: list[SelectedEvidence],
    extracted_parameters: ExtractedParameters | None,
    econ_result: EconResult | None,
    confidence_assessment: dict[str, Any],
) -> str:
    if not retrieved_chunk_list and not evidence_list:
        return "no_result"
    if econ_result is not None or _has_substantive_parameters(extracted_parameters):
        return "econ_parameterized"
    if confidence_assessment.get("label") == "low":
        return "weak_evidence"
    return "normal_hit"


def _build_summary(
    *,
    scenario: str,
    normalized_query: str,
    citations: list[dict[str, Any]],
    extracted_parameters: ExtractedParameters | None,
    econ_result: EconResult | None,
    confidence_assessment: dict[str, Any],
) -> str:
    if scenario == "no_result":
        return "未检索到可直接回答该问题的政策依据，当前不能给出有来源支撑的明确结论。"

    lead_citation = citations[0]["source"] if citations else "当前证据"
    parts = [f"围绕“{normalized_query}”，当前最相关证据来自《{lead_citation}》。"]

    if econ_result and econ_result.conclusion:
        parts.append(f"规则计算/经济学判断显示：{econ_result.conclusion}。")
    elif citations:
        parts.append(f"证据句表明：{citations[0]['quote']}。")

    if extracted_parameters and _has_substantive_parameters(extracted_parameters):
        parameter_digest = _parameter_digest(extracted_parameters)
        if parameter_digest:
            parts.append(f"已抽取的关键参数包括：{parameter_digest}。")

    if scenario == "weak_evidence":
        parts.append("但现有证据与问题匹配度偏弱，结论仅可作为初步线索。")
    else:
        label = confidence_assessment.get("label", "unknown")
        parts.append(f"当前证据置信度为 {label}。")

    return "".join(parts)


def _build_citations(
    evidence_list: list[SelectedEvidence],
    retrieved_chunk_list: list[RetrievedChunk],
) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    chunk_lookup = {item.chunk.chunk_id: item.chunk for item in retrieved_chunk_list}

    for item in evidence_list:
        chunk = chunk_lookup.get(item.chunk_id)
        source = item.metadata.get("source_title") if isinstance(item.metadata, dict) else None
        section = item.metadata.get("section_title") if isinstance(item.metadata, dict) else None
        citations.append(
            {
                "evidence_id": item.evidence_id,
                "doc_id": item.doc_id,
                "chunk_id": item.chunk_id,
                "source": source or item.citation_text or (chunk.source_title if chunk else item.doc_id),
                "section": section or (chunk.section_title if chunk else None),
                "citation_text": item.citation_text or _fallback_citation_text(chunk),
                "quote": item.evidence_text,
                "confidence": round(item.confidence, 4),
                "rationale": item.rationale,
            }
        )

    return citations


def _build_uncertainty(
    *,
    scenario: str,
    extracted_parameters: ExtractedParameters | None,
    confidence_assessment: dict[str, Any],
    retrieved_chunk_list: list[RetrievedChunk],
    evidence_list: list[SelectedEvidence],
) -> dict[str, Any]:
    missing_parameters = _find_missing_parameters(extracted_parameters)
    warning = confidence_assessment.get("warning")

    if scenario == "no_result" and warning is None:
        warning = "当前没有命中可引用的政策条款，无法输出有充分来源支撑的回答。"

    return {
        "score": confidence_assessment.get("confidence", 0.0),
        "label": confidence_assessment.get("label", "low" if scenario == "no_result" else "unknown"),
        "warning": warning,
        "reasons": confidence_assessment.get("reasons", []),
        "missing_parameters": missing_parameters,
        "retrieved_chunk_count": len(retrieved_chunk_list),
        "selected_evidence_count": len(evidence_list),
    }


def _render_final_response(
    *,
    scenario: str,
    normalized_query: str,
    summary: str,
    citations: list[dict[str, Any]],
    uncertainty: dict[str, Any],
    extracted_parameters: ExtractedParameters | None,
    econ_result: EconResult | None,
) -> str:
    policy_basis = _render_policy_basis(citations, econ_result)
    quoted_evidence = _render_quotes(citations)
    template = RESPONSE_TEMPLATES[scenario]
    return template.format(
        normalized_query=normalized_query or "",
        summary=summary,
        policy_basis=policy_basis,
        quoted_evidence=quoted_evidence,
        uncertainty=_render_uncertainty_text(uncertainty),
        parameter_block=_render_parameter_block(extracted_parameters, econ_result),
    ).strip()


def _render_policy_basis(citations: list[dict[str, Any]], econ_result: EconResult | None) -> str:
    if not citations:
        return "暂无可直接引用的政策依据。"

    lines = []
    for index, citation in enumerate(citations[:3], start=1):
        source = citation["source"]
        section = f" / {citation['section']}" if citation.get("section") else ""
        confidence = citation.get("confidence")
        line = f"{index}. {source}{section}：{citation['citation_text'] or '未提供定位信息'}"
        if confidence is not None:
            line += f"（证据置信度 {confidence:.2f}）"
        lines.append(line)

    if econ_result and econ_result.reasoning_steps:
        lines.append(f"规则补充：{'；'.join(econ_result.reasoning_steps[:2])}")

    return "\n".join(lines)


def _render_quotes(citations: list[dict[str, Any]]) -> str:
    if not citations:
        return "暂无可展示原文引用。"
    return "\n".join(
        f"- [{item['source']}] “{item['quote']}”"
        for item in citations[:3]
    )


def _render_parameter_block(
    extracted_parameters: ExtractedParameters | None,
    econ_result: EconResult | None,
) -> str:
    lines: list[str] = []
    if extracted_parameters is not None:
        if extracted_parameters.demand_scenario != DemandScenario.UNKNOWN:
            lines.append(f"- 需求场景：{extracted_parameters.demand_scenario.value}")
        for field_name, label in _NUMERIC_PARAMETER_LABELS.items():
            value = getattr(extracted_parameters, field_name)
            if value is not None:
                lines.append(f"- {label}：{value}")
        for field_name, label in _BOOL_PARAMETER_LABELS.items():
            value = getattr(extracted_parameters, field_name)
            if value is not None:
                rendered = "是" if value else "否"
                lines.append(f"- {label}：{rendered}")
        for field_name, label in _TEXT_PARAMETER_LABELS.items():
            value = getattr(extracted_parameters, field_name)
            if value:
                lines.append(f"- {label}：{value}")
        for field_name, label in _LIST_PARAMETER_LABELS.items():
            value = getattr(extracted_parameters, field_name, None)
            if value:
                rendered = ", ".join(getattr(item, "value", str(item)) for item in value)
                lines.append(f"- {label}：{rendered}")
    if econ_result is not None:
        lines.append(f"- 经济学结论：{econ_result.conclusion}")
        if econ_result.estimated_cost is not None:
            lines.append(f"- 估计成本：{econ_result.estimated_cost}")
        if econ_result.suggested_actions:
            lines.append(f"- 建议动作：{'；'.join(econ_result.suggested_actions)}")
    return "\n".join(lines) if lines else "- 暂无可稳定抽取的经济学参数。"


def _render_uncertainty_text(uncertainty: dict[str, Any]) -> str:
    warning = uncertainty.get("warning") or "未发现额外风险提示。"
    reasons = uncertainty.get("reasons") or []
    missing_parameters = uncertainty.get("missing_parameters") or []
    extras: list[str] = [
        f"置信度={uncertainty.get('label')}({uncertainty.get('score')})",
        warning,
    ]
    if reasons:
        extras.append(f"原因：{', '.join(map(str, reasons))}")
    if missing_parameters:
        extras.append(f"待补充参数：{', '.join(missing_parameters)}")
    return "；".join(extras)


def _parameter_digest(extracted_parameters: ExtractedParameters) -> str:
    digest: list[str] = []
    if extracted_parameters.loan_amount_upper_limit is not None:
        digest.append(f"额度上限 {extracted_parameters.loan_amount_upper_limit}")
    if extracted_parameters.loan_term_months is not None:
        digest.append(f"期限 {extracted_parameters.loan_term_months} 个月")
    if extracted_parameters.interest_rate is not None:
        digest.append(f"利率 {extracted_parameters.interest_rate}")
    if extracted_parameters.subsidy_rate is not None:
        digest.append(f"贴息利率 {extracted_parameters.subsidy_rate}")
    if extracted_parameters.effective_rate is not None:
        digest.append(f"有效利率 {extracted_parameters.effective_rate}")
    if extracted_parameters.target_entities:
        digest.append(f"适用主体 {'/'.join(extracted_parameters.target_entities)}")
    return "；".join(digest)


def _has_substantive_parameters(extracted_parameters: ExtractedParameters | None) -> bool:
    if extracted_parameters is None:
        return False
    if extracted_parameters.demand_scenario != DemandScenario.UNKNOWN:
        return True
    for field_name in (
        *tuple(_NUMERIC_PARAMETER_LABELS),
        *tuple(_BOOL_PARAMETER_LABELS),
        *tuple(_TEXT_PARAMETER_LABELS),
        "target_entities",
        "usage_restrictions",
        "repayment_constraints",
        "constraint_labels",
    ):
        value = getattr(extracted_parameters, field_name, None)
        if value not in (None, [], ""):
            return True
    return False


def _find_missing_parameters(extracted_parameters: ExtractedParameters | None) -> list[str]:
    if extracted_parameters is None:
        return ["地区", "主体类型", "贷款用途", "额度", "期限"]

    missing: list[str] = []
    if extracted_parameters.demand_scenario == DemandScenario.UNKNOWN:
        missing.append("需求场景")
    if extracted_parameters.target_entities == []:
        missing.append("适用主体")
    if extracted_parameters.loan_amount is None and extracted_parameters.loan_amount_upper_limit is None:
        missing.append("贷款额度")
    if extracted_parameters.loan_term_months is None:
        missing.append("贷款期限")
    if extracted_parameters.interest_rate is None and extracted_parameters.effective_rate is None:
        missing.append("利率")
    return missing


def _fallback_citation_text(chunk: Any) -> str | None:
    if chunk is None:
        return None
    section = f" - {chunk.section_title}" if getattr(chunk, "section_title", None) else ""
    return f"{chunk.source_title}{section}".strip()


def _serialize_retrieved_chunk(chunk: RetrievedChunk) -> dict[str, Any]:
    return {
        "chunk_id": chunk.chunk.chunk_id,
        "doc_id": chunk.chunk.doc_id,
        "source_title": chunk.chunk.source_title,
        "section_title": chunk.chunk.section_title,
        "retrieval_score": chunk.retrieval_score,
        "retrieval_rank": chunk.retrieval_rank,
        "match_terms": list(chunk.match_terms),
    }


def _serialize_evidence(item: SelectedEvidence) -> dict[str, Any]:
    return {
        "evidence_id": item.evidence_id,
        "chunk_id": item.chunk_id,
        "doc_id": item.doc_id,
        "evidence_text": item.evidence_text,
        "rationale": item.rationale,
        "confidence": item.confidence,
        "citation_text": item.citation_text,
        "metadata": dict(item.metadata),
    }


def _serialize_extracted_parameters(extracted_parameters: ExtractedParameters | None) -> dict[str, Any] | None:
    if extracted_parameters is None:
        return None
    return {
        "demand_scenario": extracted_parameters.demand_scenario.value,
        "constraint_labels": [item.value for item in extracted_parameters.constraint_labels],
        "loan_amount": extracted_parameters.loan_amount,
        "loan_amount_upper_limit": extracted_parameters.loan_amount_upper_limit,
        "loan_term_months": extracted_parameters.loan_term_months,
        "interest_rate": extracted_parameters.interest_rate,
        "subsidy_rate": extracted_parameters.subsidy_rate,
        "effective_rate": extracted_parameters.effective_rate,
        "collateral_required": extracted_parameters.collateral_required,
        "collateral_requirement_text": extracted_parameters.collateral_requirement_text,
        "guarantee_required": extracted_parameters.guarantee_required,
        "guarantee_requirement_text": extracted_parameters.guarantee_requirement_text,
        "target_entities": list(extracted_parameters.target_entities),
        "usage_restrictions": list(extracted_parameters.usage_restrictions),
        "repayment_constraints": list(extracted_parameters.repayment_constraints),
        "raw_slots": dict(extracted_parameters.raw_slots),
    }


def _serialize_econ_result(econ_result: EconResult | None) -> dict[str, Any] | None:
    if econ_result is None:
        return None
    return {
        "conclusion": econ_result.conclusion,
        "confidence": econ_result.confidence,
        "demand_scenario": econ_result.demand_scenario.value,
        "constraint_labels": [item.value for item in econ_result.constraint_labels],
        "estimated_cost": econ_result.estimated_cost,
        "suggested_actions": list(econ_result.suggested_actions),
        "reasoning_steps": list(econ_result.reasoning_steps),
        "metadata": dict(econ_result.metadata),
    }


def _serialize_session_state(session_state: SessionState) -> dict[str, Any]:
    return {
        "session_id": session_state.session_id,
        "user_id": session_state.user_id,
        "current_region": session_state.current_region,
        "normalized_query": session_state.normalized_query,
        "demand_scenario": session_state.demand_scenario.value,
        "purpose": session_state.purpose,
        "amount": session_state.amount,
        "crop_or_activity": session_state.crop_or_activity,
        "duration": session_state.duration,
        "existing_loan": session_state.existing_loan,
        "cooperative": session_state.cooperative,
        "guarantor": session_state.guarantor,
        "collateral": session_state.collateral,
        "updated_at": session_state.updated_at.isoformat() if session_state.updated_at else None,
        "metadata": dict(session_state.metadata),
    }


__all__ = ["build_structured_response"]
