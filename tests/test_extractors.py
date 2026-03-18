from __future__ import annotations

from src.extract.parameter_parser import parse_extracted_parameters
from src.extract.regex_extractors import extract_first_pass_slots


def test_extractors_pull_key_finance_slots_from_evidence_and_metadata() -> None:
    evidence_text = '贷款额度最高50万元，期限12个月，执行利率3.2%，财政贴息1.2%。申请人需提供抵押和担保。'
    metadata = {'chunk_text': evidence_text, 'section_title': '支持范围', 'source_title': '设施农业贷款政策'}

    slots = extract_first_pass_slots(evidence_text, metadata)
    extracted = parse_extracted_parameters(evidence_text, metadata)

    assert slots['loan_amount_upper_limit'] == 500000.0
    assert slots['loan_term_months'] == 12
    assert slots['interest_rate'] == 3.2
    assert slots['subsidy_rate'] == 1.2
    assert slots['collateral_required'] is True
    assert slots['guarantee_required'] is True
    assert extracted.effective_rate == 2.0
