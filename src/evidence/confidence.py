"""Heuristics for evidence confidence and low-confidence warnings."""

from __future__ import annotations

from typing import Iterable

from src.common import SelectedEvidence
from src.retrieve.index_store import tokenize_for_retrieval

_GENERIC_INTRO_PATTERNS = (
    "为贯彻",
    "根据",
    "现将",
    "通知如下",
    "工作要求",
    "总体要求",
    "指导思想",
)



def assess_evidence_confidence(query: str, evidence: Iterable[SelectedEvidence]) -> dict[str, object]:
    """Return a simple, inspectable confidence assessment for selected evidence."""

    evidence_list = list(evidence)
    query_terms = set(tokenize_for_retrieval(query))
    if not query_terms:
        return {
            "confidence": 0.1,
            "label": "low",
            "warning": "查询缺少可用于匹配的关键词，证据置信度较低。",
            "reasons": ["empty_query_terms"],
        }

    if not evidence_list:
        return {
            "confidence": 0.08,
            "label": "low",
            "warning": "未选出有效证据句，建议放宽检索或提示用户补充条件。",
            "reasons": ["no_evidence"],
        }

    matched_terms: set[str] = set()
    generic_hits = 0
    best_sentence_overlap = 0
    evidence_confidences: list[float] = []

    for item in evidence_list:
        sentence_terms = set(tokenize_for_retrieval(item.evidence_text))
        overlap = len(query_terms & sentence_terms)
        best_sentence_overlap = max(best_sentence_overlap, overlap)
        matched_terms.update(query_terms & sentence_terms)
        evidence_confidences.append(item.confidence)
        if _looks_generic(item.evidence_text, overlap):
            generic_hits += 1

    coverage = len(matched_terms) / max(len(query_terms), 1)
    avg_evidence_confidence = sum(evidence_confidences) / max(len(evidence_confidences), 1)
    score = avg_evidence_confidence * 0.55 + coverage * 0.45
    reasons: list[str] = []
    warning: str | None = None

    if best_sentence_overlap <= 1:
        score -= 0.22
        reasons.append("weak_term_overlap")
    if coverage < 0.35:
        score -= 0.18
        reasons.append("low_query_coverage")
    if generic_hits == len(evidence_list):
        score -= 0.15
        reasons.append("generic_intro_only")

    score = max(0.0, min(score, 1.0))
    label = "high" if score >= 0.75 else "medium" if score >= 0.45 else "low"

    if label == "low":
        if "generic_intro_only" in reasons:
            warning = "当前命中的多为政策导语或一般性说明，缺少直接回答问题的条款。"
        elif "low_query_coverage" in reasons:
            warning = "证据句覆盖的查询关键词较少，回答可能不够准确，建议补充更具体条件。"
        else:
            warning = "查询与证据句匹配较弱，建议回退为低置信提示或请求用户澄清。"

    return {
        "confidence": round(score, 4),
        "label": label,
        "warning": warning,
        "reasons": reasons,
        "matched_terms": sorted(matched_terms),
        "coverage": round(coverage, 4),
        "best_sentence_overlap": best_sentence_overlap,
        "generic_hits": generic_hits,
    }



def _looks_generic(text: str, overlap: int) -> bool:
    return overlap <= 2 and any(pattern in text for pattern in _GENERIC_INTRO_PATTERNS)


__all__ = ["assess_evidence_confidence"]
