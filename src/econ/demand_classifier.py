"""Explicit demand-scenario rules derived from user intent and policy wording."""

from __future__ import annotations

from src.common.enums import DemandScenario


_DEMAND_RULES: list[tuple[DemandScenario, tuple[str, ...]]] = [
    (
        DemandScenario.CROP_INPUT_PURCHASE,
        ("化肥", "肥料", "种子", "饲料", "农药", "农资", "农膜"),
    ),
    (
        DemandScenario.EQUIPMENT_PURCHASE,
        ("设备购置", "购机", "农机", "机器设备", "机具", "生产设备"),
    ),
    (
        DemandScenario.INFRASTRUCTURE,
        ("基础设施", "高标准农田", "水利", "冷库", "厂房", "棚舍", "仓储"),
    ),
    (
        DemandScenario.SEASONAL_PRODUCTION,
        ("春耕", "秋收", "备耕", "备播", "当季生产", "农业生产周期"),
    ),
    (
        DemandScenario.EMERGENCY_RELIEF,
        ("救灾", "灾后恢复", "应急", "纾困", "稳产保供"),
    ),
    (
        DemandScenario.EXPANSION,
        ("扩建", "扩产", "新增产能", "扩大规模", "项目建设"),
    ),
    (
        DemandScenario.WORKING_CAPITAL,
        ("流动资金", "周转", "采购", "经营周转", "补充流动资金"),
    ),
]


def classify_demand_scenario(text: str) -> DemandScenario:
    """Return the first matching demand scenario from explicit keywords."""

    normalized_text = text.strip()
    if not normalized_text:
        return DemandScenario.UNKNOWN

    for scenario, keywords in _DEMAND_RULES:
        if any(keyword in normalized_text for keyword in keywords):
            return scenario
    return DemandScenario.UNKNOWN


__all__ = ["classify_demand_scenario"]
