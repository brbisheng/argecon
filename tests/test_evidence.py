from __future__ import annotations

from src.common import ChunkRecord, RetrievedChunk, SelectedEvidence
from src.evidence.confidence import assess_evidence_confidence
from src.evidence.sentence_selector import rank_candidate_sentences, select_evidence_sentences
from src.evidence.sentence_splitter import split_sentences



def _retrieved_chunk(chunk_id: str, text: str, *, title: str = "政策", score: float = 0.8) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=ChunkRecord(
            chunk_id=chunk_id,
            doc_id=chunk_id.split(":")[0],
            region="fujian",
            source_title=title,
            chunk_text=text,
            chunk_index=0,
            section_title="支持范围",
        ),
        retrieval_score=score,
        retrieval_rank=1,
        match_terms=[],
        retriever_name="bm25",
    )



def test_split_sentences_handles_policy_punctuation_and_article_markers() -> None:
    text = (
        "第二条 支持对象。对符合条件的家庭农场给予贴息支持；"
        "（一）贷款用于购买农资。"
        "（二）贷款额度最高50万元。"
    )

    sentences = split_sentences(text)

    assert "第二条 支持对象。" in sentences
    assert "对符合条件的家庭农场给予贴息支持；" in sentences
    assert "（一）贷款用于购买农资。" in sentences
    assert "（二）贷款额度最高50万元。" in sentences



def test_rank_and_select_evidence_prefers_high_query_coverage_sentences() -> None:
    chunks = [
        _retrieved_chunk(
            "doc-1:0",
            "为贯彻相关要求，现将有关事项通知如下。对符合条件的养殖场提供贴息贷款支持，重点支持扩栏和圈舍改造。",
            title="生猪养殖贷款贴息政策",
            score=0.95,
        ),
        _retrieved_chunk(
            "doc-2:0",
            "申请材料包括营业执照、身份证明等基础材料。",
            title="申请材料说明",
            score=0.55,
        ),
    ]

    ranked = rank_candidate_sentences("生猪养殖 贴息贷款", chunks, top_k_chunks=2)
    selected = select_evidence_sentences("生猪养殖 贴息贷款", chunks, top_k_chunks=2, max_sentences=2)

    assert ranked
    assert ranked[0].sentence == "对符合条件的养殖场提供贴息贷款支持，重点支持扩栏和圈舍改造。"
    assert selected[0].evidence_text == ranked[0].sentence
    assert selected[0].metadata["coverage"] > 0
    assert "贴息贷款" in selected[0].metadata["matched_terms"]



def test_assess_evidence_confidence_marks_generic_or_weak_matches_low() -> None:
    evidence = [
        SelectedEvidence(
            evidence_id="doc-1:0:sent-1",
            chunk_id="doc-1:0",
            doc_id="doc-1",
            evidence_text="为贯彻落实金融支持政策，现将有关事项通知如下。",
            confidence=0.32,
        )
    ]

    assessment = assess_evidence_confidence("贴息贷款额度", evidence)

    assert assessment["label"] == "low"
    assert assessment["warning"] is not None
    assert assessment["reasons"]
