"""Regex-based first-pass extractors for finance-related evidence text."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


_PERCENT_PATTERN = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*(?:%|％)")
_TERM_MONTH_PATTERN = re.compile(r"(?P<value>\d{1,3})\s*个?月")
_TERM_YEAR_PATTERN = re.compile(r"(?P<value>\d{1,2})\s*年")
_AMOUNT_PATTERN = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>亿元|万元|万|千元|元)"
)
_TARGET_ENTITY_PATTERN = re.compile(
    r"(?:适用对象|支持对象|适用主体|服务对象|扶持对象|贷款对象|面向)"
    r"[:：]?\s*([^。；;\n]+)"
)
_USAGE_PATTERN = re.compile(
    r"(?:贷款用途|资金用途|用于|专项用于|仅限用于|不得用于|禁止用于)"
    r"[:：]?\s*([^。；;\n]+)"
)
_REPAYMENT_PATTERN = re.compile(
    r"(?:还款方式|还款要求|还款约束|偿还方式|到期还本|按月付息|分期还款|随借随还)"
    r"[:：]?\s*([^。；;\n]+)?"
)

_INTEREST_HINTS = ("利率", "年利率", "执行利率", "贷款利率", "综合利率")
_SUBSIDY_HINTS = ("贴息", "财政贴息", "补贴比例", "贴息比例", "利息补助")
_AMOUNT_UPPER_HINTS = ("最高", "上限", "不超过", "最高可贷", "额度")
_COLLATERAL_HINTS = ("抵押", "质押", "抵押物", "担保物")
_GUARANTEE_HINTS = ("担保", "保证人", "第三方保证", "连带责任保证")


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _clean_extracted_fragment(text: str) -> str:
    cleaned = _normalize_whitespace(text).strip("：:，,、 ")
    return re.sub(r"^(?:为|是)", "", cleaned).strip()


def _iter_text_candidates(
    evidence_text: str,
    chunk_metadata: Mapping[str, Any] | None,
) -> list[str]:
    candidates = [evidence_text]
    if not chunk_metadata:
        return [_normalize_whitespace(item) for item in candidates if item]

    for key in ("chunk_text", "section_title", "source_title", "title"):
        value = chunk_metadata.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(value)

    metadata = chunk_metadata.get("metadata")
    if isinstance(metadata, Mapping):
        for value in metadata.values():
            if isinstance(value, str) and value.strip():
                candidates.append(value)
            elif isinstance(value, (list, tuple, set)):
                candidates.extend(str(item) for item in value if str(item).strip())

    return [_normalize_whitespace(item) for item in candidates if item]


def _extract_percent_with_hints(texts: list[str], hints: tuple[str, ...]) -> float | None:
    for text in texts:
        for hint in hints:
            pattern = re.compile(
                rf"{re.escape(hint)}[^%％\d]{{0,12}}(?P<value>\d+(?:\.\d+)?)\s*(?:%|％)"
            )
            match = pattern.search(text)
            if match:
                return float(match.group("value"))
    return None


def _extract_term_months(texts: list[str]) -> int | None:
    for text in texts:
        month_match = _TERM_MONTH_PATTERN.search(text)
        if month_match:
            return int(month_match.group("value"))
        year_match = _TERM_YEAR_PATTERN.search(text)
        if year_match:
            return int(year_match.group("value")) * 12
    return None


def _to_yuan(value: float, unit: str) -> float:
    unit_multiplier = {
        "元": 1,
        "千元": 1_000,
        "万": 10_000,
        "万元": 10_000,
        "亿元": 100_000_000,
    }
    return value * unit_multiplier[unit]


def _extract_amount_upper_limit(texts: list[str]) -> float | None:
    for text in texts:
        for match in _AMOUNT_PATTERN.finditer(text):
            span_start = max(0, match.start() - 16)
            prefix = text[span_start : match.start()]
            if any(hint in prefix for hint in _AMOUNT_UPPER_HINTS):
                return _to_yuan(float(match.group("value")), match.group("unit"))
    return None


def _extract_requirement(
    texts: list[str],
    hints: tuple[str, ...],
) -> tuple[bool | None, str | None]:
    negative_markers = ("免", "无需", "不需", "无须", "信用")
    positive_markers = ("需", "须", "应", "提供", "落实", "追加", "具备")
    for text in texts:
        for hint in hints:
            if hint not in text:
                continue
            sentence_match = re.search(rf"[^。；;\n]*{re.escape(hint)}[^。；;\n]*", text)
            sentence = sentence_match.group(0).strip() if sentence_match else hint
            if any(marker in sentence for marker in negative_markers):
                return False, sentence
            if any(marker in sentence for marker in positive_markers) or hint in sentence:
                return True, sentence
    return None, None


def _extract_list_by_pattern(texts: list[str], pattern: re.Pattern[str]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for match in pattern.finditer(text):
            candidate = _clean_extracted_fragment(
                match.group(1) if match.lastindex else match.group(0)
            )
            if candidate and candidate not in seen:
                seen.add(candidate)
                values.append(candidate)
    return values


def extract_first_pass_slots(
    evidence_text: str,
    chunk_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract explicit parameters from evidence text and chunk metadata."""

    texts = _iter_text_candidates(evidence_text, chunk_metadata)
    interest_rate = _extract_percent_with_hints(texts, _INTEREST_HINTS)
    subsidy_rate = _extract_percent_with_hints(texts, _SUBSIDY_HINTS)
    loan_term_months = _extract_term_months(texts)
    loan_amount_upper_limit = _extract_amount_upper_limit(texts)
    collateral_required, collateral_requirement_text = _extract_requirement(
        texts,
        _COLLATERAL_HINTS,
    )
    guarantee_required, guarantee_requirement_text = _extract_requirement(
        texts,
        _GUARANTEE_HINTS,
    )
    target_entities = _extract_list_by_pattern(texts, _TARGET_ENTITY_PATTERN)
    usage_restrictions = _extract_list_by_pattern(texts, _USAGE_PATTERN)
    repayment_constraints = _extract_list_by_pattern(texts, _REPAYMENT_PATTERN)

    matched_rates = [float(match.group("value")) for text in texts for match in _PERCENT_PATTERN.finditer(text)]

    return {
        "interest_rate": interest_rate,
        "subsidy_rate": subsidy_rate,
        "loan_term_months": loan_term_months,
        "loan_amount_upper_limit": loan_amount_upper_limit,
        "collateral_required": collateral_required,
        "collateral_requirement_text": collateral_requirement_text,
        "guarantee_required": guarantee_required,
        "guarantee_requirement_text": guarantee_requirement_text,
        "target_entities": target_entities,
        "usage_restrictions": usage_restrictions,
        "repayment_constraints": repayment_constraints,
        "matched_percentages": matched_rates,
        "source_texts": texts,
    }


__all__ = ["extract_first_pass_slots"]
