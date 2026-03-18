"""Rule-based slot extraction and per-session state updates."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.common.schemas import SelectedEvidence
from src.memory.session_state import DEFAULT_SESSION_STORE, SessionState, SessionStateStore


_ACTIVITY_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"养牛|肉牛|奶牛"), "养牛"),
    (re.compile(r"养猪|生猪|育肥猪|母猪"), "养猪"),
    (re.compile(r"养羊"), "养羊"),
    (re.compile(r"养鸡|蛋鸡|肉鸡"), "养鸡"),
    (re.compile(r"养鱼|水产|渔业|养虾"), "水产养殖"),
    (re.compile(r"种粮|粮食|小麦|玉米|水稻"), "粮食种植"),
    (re.compile(r"果园|苹果|柑橘|葡萄|猕猴桃"), "水果种植"),
    (re.compile(r"蔬菜|大棚|设施农业"), "设施农业"),
)

_PURPOSE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"买化肥|化肥|种子|农药|饲料|农资"), "农业生产资料投入"),
    (re.compile(r"周转|流动资金|经营周转"), "经营周转"),
    (re.compile(r"扩建|扩大|新建|建棚|建圈舍"), "扩大生产"),
    (re.compile(r"购置设备|买设备|农机|机器"), "设备购置"),
)

_AMOUNT_PATTERN = re.compile(r"((?:\d+(?:\.\d+)?)\s*(?:万元|万|元))")
_DURATION_PATTERN = re.compile(r"((?:\d+(?:\.\d+)?)\s*(?:个月|月|年)|半年|一年|两年|三年)")
_EXISTING_LOAN_TRUE_PATTERN = re.compile(r"没还完|未还完|未结清|没结清|还有.*没还|还有一点没还|续贷|展期|旧贷")
_EXISTING_LOAN_FALSE_PATTERN = re.compile(r"没有贷款|无贷款|已还清|都还完了|没有未结清")
_COOPERATIVE_TRUE_PATTERN = re.compile(r"合作社")
_COOPERATIVE_FALSE_PATTERN = re.compile(r"不是合作社|非合作社")
_GUARANTOR_TRUE_PATTERN = re.compile(r"担保人|保证人|有人担保|找人担保")
_GUARANTOR_FALSE_PATTERN = re.compile(r"没有担保人|无担保人|没人担保")
_COLLATERAL_TRUE_PATTERN = re.compile(r"抵押|抵押物|房产作抵押|有抵押物|有抵押")
_COLLATERAL_FALSE_PATTERN = re.compile(r"无抵押|没有抵押|没抵押物")


def update_session_state(
    query: str,
    evidence: Iterable["SelectedEvidence" | str] | None = None,
    *,
    session_id: str | None = None,
    session_state: SessionState | None = None,
    store: SessionStateStore = DEFAULT_SESSION_STORE,
) -> SessionState:
    """Update V1 session slot memory using the current query and this turn's evidence."""

    if session_state is None:
        if not session_id:
            msg = "session_id is required when session_state is not provided"
            raise ValueError(msg)
        session_state = store.get_or_create(session_id)
    elif session_id and session_id != session_state.session_id:
        msg = "session_id does not match session_state.session_id"
        raise ValueError(msg)

    combined_text = "\n".join(part for part in [query.strip(), *_flatten_evidence_texts(evidence)] if part)
    updates = {
        "normalized_query": query.strip() or session_state.normalized_query,
        "purpose": _extract_first_match(combined_text, _PURPOSE_PATTERNS),
        "amount": _extract_group(combined_text, _AMOUNT_PATTERN),
        "crop_or_activity": _extract_first_match(combined_text, _ACTIVITY_PATTERNS),
        "duration": _extract_group(combined_text, _DURATION_PATTERN),
        "existing_loan": _extract_bool(combined_text, _EXISTING_LOAN_TRUE_PATTERN, _EXISTING_LOAN_FALSE_PATTERN),
        "cooperative": _extract_bool(combined_text, _COOPERATIVE_TRUE_PATTERN, _COOPERATIVE_FALSE_PATTERN),
        "guarantor": _extract_bool(combined_text, _GUARANTOR_TRUE_PATTERN, _GUARANTOR_FALSE_PATTERN),
        "collateral": _extract_bool(combined_text, _COLLATERAL_TRUE_PATTERN, _COLLATERAL_FALSE_PATTERN),
    }
    session_state.apply_updates(**updates)
    return store.save(session_state)


def _flatten_evidence_texts(evidence: Iterable["SelectedEvidence" | str] | None) -> list[str]:
    if evidence is None:
        return []

    texts: list[str] = []
    for item in evidence:
        if isinstance(item, str):
            text = item.strip()
        else:
            text = item.evidence_text.strip()
        if text:
            texts.append(text)
    return texts


def _extract_first_match(text: str, patterns: tuple[tuple[re.Pattern[str], str], ...]) -> str | None:
    for pattern, normalized_value in patterns:
        if pattern.search(text):
            return normalized_value
    return None


def _extract_group(text: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(text)
    if match is None:
        return None
    return re.sub(r"\s+", "", match.group(1))


def _extract_bool(text: str, true_pattern: re.Pattern[str], false_pattern: re.Pattern[str]) -> bool | None:
    if false_pattern.search(text):
        return False
    if true_pattern.search(text):
        return True
    return None


__all__ = ["update_session_state"]
