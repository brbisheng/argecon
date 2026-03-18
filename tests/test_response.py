from __future__ import annotations

from src.common import ChunkRecord, EconResult, ExtractedParameters, RetrievedChunk, SelectedEvidence, SessionState
from src.common.enums import ConstraintLabel, DemandScenario
from src.response.response_builder import build_structured_response



def _chunk(chunk_id: str, text: str, *, title: str = "政策A", score: float = 0.91) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=ChunkRecord(
            chunk_id=chunk_id,
            doc_id=chunk_id.split(":")[0],
            region="beijing",
            source_title=title,
            chunk_text=text,
            chunk_index=0,
            section_title="支持范围",
        ),
        retrieval_score=score,
        retrieval_rank=1,
        match_terms=["贴息贷款", "养殖"],
        retriever_name="bm25",
    )



def _session() -> SessionState:
    return SessionState(session_id="sess-1", current_region="beijing")



def test_build_structured_response_returns_normal_hit_with_grounded_text() -> None:
    retrieved = [_chunk("doc-1:0", "对符合条件的养殖场提供贴息贷款支持。")]
    evidence = [
        SelectedEvidence(
            evidence_id="doc-1:0:sent-1",
            chunk_id="doc-1:0",
            doc_id="doc-1",
            evidence_text="对符合条件的养殖场提供贴息贷款支持。",
            confidence=0.88,
            citation_text="生猪养殖贴息政策 - 支持范围",
            metadata={"source_title": "生猪养殖贴息政策", "section_title": "支持范围"},
        )
    ]

    response = build_structured_response(
        normalized_query="生猪养殖 贴息贷款",
        retrieved_chunks=retrieved,
        selected_evidence=evidence,
        extracted_parameters=None,
        econ_result=None,
        session_state=_session(),
    )

    assert response["scenario"] == "normal_hit"
    assert response["citations"][0]["source"] == "生猪养殖贴息政策"
    assert "最相关政策依据" in response["final_response"]
    assert "原文引用" in response["final_response"]
    assert "对符合条件的养殖场提供贴息贷款支持。" in response["summary"]



def test_build_structured_response_marks_weak_evidence_when_confidence_is_low() -> None:
    retrieved = [_chunk("doc-2:0", "为贯彻相关要求，现将有关事项通知如下。", score=0.62)]
    evidence = [
        SelectedEvidence(
            evidence_id="doc-2:0:sent-1",
            chunk_id="doc-2:0",
            doc_id="doc-2",
            evidence_text="为贯彻相关要求，现将有关事项通知如下。",
            confidence=0.22,
            citation_text="一般性通知 - 导语",
            metadata={"source_title": "一般性通知", "section_title": "导语"},
        )
    ]

    response = build_structured_response(
        normalized_query="贴息贷款额度",
        retrieved_chunks=retrieved,
        selected_evidence=evidence,
        extracted_parameters=None,
        econ_result=None,
        session_state=_session(),
    )

    assert response["scenario"] == "weak_evidence"
    assert response["uncertainty"]["label"] == "low"
    assert "弱证据" in response["final_response"]
    assert "建议：请补充地区" in response["final_response"]



def test_build_structured_response_returns_no_result_fallback_without_evidence() -> None:
    response = build_structured_response(
        normalized_query="合作社周转贷款 申请条件",
        retrieved_chunks=[],
        selected_evidence=[],
        extracted_parameters=None,
        econ_result=None,
        session_state=_session(),
    )

    assert response["scenario"] == "no_result"
    assert response["citations"] == []
    assert "暂无可展示原文引用" in response["final_response"]
    assert "不能给出有来源支撑的明确结论" in response["summary"]



def test_build_structured_response_includes_econ_parameters_and_trace() -> None:
    retrieved = [_chunk("doc-3:0", "贷款额度最高50万元，期限12个月，给予贴息支持。", title="设施农业贷款政策")]
    evidence = [
        SelectedEvidence(
            evidence_id="doc-3:0:sent-1",
            chunk_id="doc-3:0",
            doc_id="doc-3",
            evidence_text="贷款额度最高50万元，期限12个月，给予贴息支持。",
            confidence=0.93,
            citation_text="设施农业贷款政策 - 支持范围",
            metadata={"source_title": "设施农业贷款政策", "section_title": "支持范围"},
        )
    ]
    parameters = ExtractedParameters(
        demand_scenario=DemandScenario.WORKING_CAPITAL,
        constraint_labels=[ConstraintLabel.LOAN_AMOUNT, ConstraintLabel.TERM],
        loan_amount_upper_limit=50.0,
        loan_term_months=12,
        interest_rate=3.6,
        subsidy_rate=1.2,
        effective_rate=2.4,
        target_entities=["家庭农场"],
    )
    econ_result = EconResult(
        conclusion="在贴息后综合融资成本下降，可优先考虑该产品。",
        confidence=0.81,
        demand_scenario=DemandScenario.WORKING_CAPITAL,
        constraint_labels=[ConstraintLabel.LOAN_AMOUNT],
        estimated_cost=2.4,
        suggested_actions=["核实主体资质", "确认贴息期限"],
        reasoning_steps=["根据名义利率与补贴利率计算有效利率", "额度与期限来自政策条款"],
    )

    response = build_structured_response(
        normalized_query="设施农业贷款 额度 利率",
        retrieved_chunks=retrieved,
        selected_evidence=evidence,
        extracted_parameters=parameters,
        econ_result=econ_result,
        session_state=_session(),
    )

    assert response["scenario"] == "econ_parameterized"
    assert "经济学参数" in response["final_response"]
    assert "有效利率：2.4" in response["final_response"]
    assert response["trace"]["extracted_parameters"]["loan_amount_upper_limit"] == 50.0
    assert response["trace"]["econ_result"]["estimated_cost"] == 2.4
