"""Explicit rule set for normalizing policy/product constraints."""

from __future__ import annotations

from src.common.enums import ConstraintLabel
from src.common.schemas import ExtractedParameters


_KEYWORD_RULES: list[tuple[ConstraintLabel, tuple[str, ...]]] = [
    (ConstraintLabel.COLLATERAL, ("抵押", "质押", "抵押物")),
    (ConstraintLabel.GUARANTEE, ("担保", "保证人", "第三方保证")),
    (ConstraintLabel.EXISTING_DEBT_CONSTRAINT, ("未结清贷款", "续贷", "展期", "借新还旧", "存量贷款")),
    (ConstraintLabel.LOAN_AMOUNT, ("最高", "额度", "上限", "不超过")),
    (ConstraintLabel.TERM, ("期限", "月", "年")),
    (ConstraintLabel.INTEREST_RATE, ("利率", "贴息", "补贴比例")),
    (ConstraintLabel.PURPOSE_RESTRICTION, ("贷款用途", "用于", "仅限用于", "不得用于", "禁止用于")),
    (ConstraintLabel.REPAYMENT, ("还款", "付息", "到期还本", "分期偿还", "提前还款")),
    (ConstraintLabel.ELIGIBILITY, ("适用对象", "适用主体", "申请条件", "准入条件")),
    (ConstraintLabel.REGION, ("本地区", "辖内", "属地", "县域", "行政区域")),
    (ConstraintLabel.INDUSTRY, ("农业", "养殖", "种植", "农机", "粮食")),
    (ConstraintLabel.CREDIT, ("征信", "信用记录", "信用状况", "失信")),
]


def detect_constraint_labels(
    text: str,
    parameters: ExtractedParameters | None = None,
) -> list[ConstraintLabel]:
    """Detect normalized constraint labels from explicit wording and parsed fields."""

    labels: list[ConstraintLabel] = []
    normalized_text = text.strip()

    for label, keywords in _KEYWORD_RULES:
        if any(keyword in normalized_text for keyword in keywords):
            labels.append(label)

    if parameters:
        if parameters.collateral_required is not None and ConstraintLabel.COLLATERAL not in labels:
            labels.append(ConstraintLabel.COLLATERAL)
        if parameters.guarantee_required is not None and ConstraintLabel.GUARANTEE not in labels:
            labels.append(ConstraintLabel.GUARANTEE)
        if parameters.loan_amount_upper_limit is not None and ConstraintLabel.LOAN_AMOUNT not in labels:
            labels.append(ConstraintLabel.LOAN_AMOUNT)
        if parameters.loan_term_months is not None and ConstraintLabel.TERM not in labels:
            labels.append(ConstraintLabel.TERM)
        if (
            parameters.interest_rate is not None or parameters.subsidy_rate is not None
        ) and ConstraintLabel.INTEREST_RATE not in labels:
            labels.append(ConstraintLabel.INTEREST_RATE)
        if parameters.usage_restrictions and ConstraintLabel.PURPOSE_RESTRICTION not in labels:
            labels.append(ConstraintLabel.PURPOSE_RESTRICTION)
        if parameters.repayment_constraints and ConstraintLabel.REPAYMENT not in labels:
            labels.append(ConstraintLabel.REPAYMENT)
        if parameters.target_entities and ConstraintLabel.ELIGIBILITY not in labels:
            labels.append(ConstraintLabel.ELIGIBILITY)

    return labels


__all__ = ["detect_constraint_labels"]
