from __future__ import annotations

from src.common import ChunkRecord, RetrievedChunk, SelectedEvidence, SessionState
from src.response.response_builder import build_structured_response


def _retrieved_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk=ChunkRecord(
            chunk_id='doc-1:0',
            doc_id='doc-1',
            region='北京',
            source_title='设施农业贷款政策',
            chunk_text='贷款额度最高50万元，期限12个月，执行利率3.2%。',
            chunk_index=0,
            section_title='支持范围',
        ),
        retrieval_score=0.95,
        retrieval_rank=1,
        match_terms=['额度', '期限', '利率'],
        retriever_name='bm25',
    )


def _session() -> SessionState:
    return SessionState(session_id='sess-1', current_region='北京')


def test_response_builder_returns_grounded_answer_when_evidence_exists() -> None:
    retrieved = [_retrieved_chunk()]
    evidence = [
        SelectedEvidence(
            evidence_id='ev-1',
            chunk_id='doc-1:0',
            doc_id='doc-1',
            evidence_text='贷款额度最高50万元，期限12个月，执行利率3.2%。',
            confidence=0.93,
            citation_text='设施农业贷款政策 - 支持范围',
            metadata={'source_title': '设施农业贷款政策', 'section_title': '支持范围'},
        )
    ]

    response = build_structured_response('贷款额度最高50万元 期限12个月 执行利率3.2%', retrieved, evidence, None, None, _session())

    assert response['scenario'] == 'normal_hit'
    assert '设施农业贷款政策' in response['final_response']
    assert '贷款额度最高50万元' in response['summary']
    assert response['citations'][0]['source'] == '设施农业贷款政策'


def test_response_builder_falls_back_when_no_evidence_exists() -> None:
    response = build_structured_response('合作社贷款条件', [], [], None, None, _session())

    assert response['scenario'] == 'no_result'
    assert response['citations'] == []
    assert '不能给出有来源支撑的明确结论' in response['summary']
    assert '暂无可展示原文引用' in response['final_response']
