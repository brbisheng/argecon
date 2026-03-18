"""Fixed response templates for evidence-grounded policy answers."""

from __future__ import annotations

from typing import Final

NORMAL_HIT_TEMPLATE: Final[str] = """问题归一化：{normalized_query}

结论摘要：{summary}

最相关政策依据：
{policy_basis}

原文引用：
{quoted_evidence}

不确定性提示：{uncertainty}
"""

WEAK_EVIDENCE_TEMPLATE: Final[str] = """问题归一化：{normalized_query}

结论摘要：{summary}

最相关政策依据（弱证据）：
{policy_basis}

原文引用：
{quoted_evidence}

不确定性提示：{uncertainty}

建议：请补充地区、主体类型、贷款用途、额度或期限，以便缩小检索范围。
"""

NO_RESULT_TEMPLATE: Final[str] = """问题归一化：{normalized_query}

结论摘要：{summary}

最相关政策依据：当前未检索到可直接支撑回答的政策条款。

原文引用：暂无可展示原文引用。

不确定性提示：{uncertainty}

建议：请补充地区、政策名称、产品名称、主体类型或资金用途后重试。
"""

ECON_PARAMETER_TEMPLATE: Final[str] = """问题归一化：{normalized_query}

结论摘要：{summary}

经济学参数：
{parameter_block}

最相关政策依据：
{policy_basis}

原文引用：
{quoted_evidence}

不确定性提示：{uncertainty}
"""

RESPONSE_TEMPLATES: Final[dict[str, str]] = {
    "normal_hit": NORMAL_HIT_TEMPLATE,
    "weak_evidence": WEAK_EVIDENCE_TEMPLATE,
    "no_result": NO_RESULT_TEMPLATE,
    "econ_parameterized": ECON_PARAMETER_TEMPLATE,
}

__all__ = [
    "ECON_PARAMETER_TEMPLATE",
    "NORMAL_HIT_TEMPLATE",
    "NO_RESULT_TEMPLATE",
    "RESPONSE_TEMPLATES",
    "WEAK_EVIDENCE_TEMPLATE",
]
