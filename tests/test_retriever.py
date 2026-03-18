from __future__ import annotations

import json
from pathlib import Path

from src.retrieve.bm25_retriever import BM25Retriever
from src.retrieve.index_store import ChunkIndexStore, load_chunk_index, tokenize_for_retrieval
from src.retrieve.tfidf_retriever import TfidfRetriever


KB_CHUNKS = [
    {
        "chunk_id": "doc-1:0",
        "doc_id": "doc-1",
        "region": "sichuan",
        "source_title": "生猪养殖贷款贴息政策",
        "chunk_index": 0,
        "chunk_text": "对符合条件的生猪养殖场提供贴息贷款支持，重点支持扩栏和圈舍改造。",
        "metadata": {"source_path": "policies/doc-1.md", "policy_type": "subsidized_loan"},
    },
    {
        "chunk_id": "doc-2:0",
        "doc_id": "doc-2",
        "region": "anhui",
        "source_title": "农机购置补贴办法",
        "chunk_index": 0,
        "chunk_text": "农机购置补贴面向合作社，补贴比例按照设备类型分类执行。",
        "metadata": {"source_path": "policies/doc-2.md", "policy_type": "equipment_subsidy"},
    },
]

CANONICAL_CHUNKS = [
    {
        "chunk_id": "doc-3:0",
        "doc_id": "doc-3",
        "region": "henan",
        "source_title": "粮食收储周转贷款",
        "chunk_index": 0,
        "chunk_text": "对粮食收储企业提供短期周转贷款，用于旺季收购资金安排。",
        "section_title": "支持范围",
        "metadata": {"source_path": "policies/doc-3.md"},
    }
]


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        for record in records:
            file_obj.write(json.dumps(record, ensure_ascii=False) + "\n")



def test_index_store_prefers_kb_chunks_when_present(tmp_path: Path) -> None:
    _write_jsonl(tmp_path / "chunks.jsonl", CANONICAL_CHUNKS)
    _write_jsonl(tmp_path / "kb_chunks.jsonl", KB_CHUNKS)

    index = load_chunk_index(data_dir=tmp_path)

    assert [chunk.chunk_id for chunk in index.chunks] == ["doc-1:0", "doc-2:0"]
    assert index.metadata["source_path"].endswith("kb_chunks.jsonl")
    assert "贴息贷款" in index.tokenized_chunks[0]



def test_bm25_retriever_returns_ranked_retrieved_chunks(tmp_path: Path) -> None:
    _write_jsonl(tmp_path / "kb_chunks.jsonl", KB_CHUNKS)
    retriever = BM25Retriever.from_chunk_store(data_dir=str(tmp_path))

    results = retriever.retrieve("生猪 贴息贷款", top_k=2)

    assert len(results) == 1
    top_hit = results[0]
    assert top_hit.chunk.chunk_id == "doc-1:0"
    assert top_hit.chunk.source_title == "生猪养殖贷款贴息政策"
    assert top_hit.chunk.region == "sichuan"
    assert "贴息贷款" in top_hit.chunk.chunk_text
    assert top_hit.chunk.metadata["policy_type"] == "subsidized_loan"
    assert top_hit.retrieval_score > 0
    assert top_hit.match_terms



def test_tfidf_retriever_supports_region_filter_and_fallback(tmp_path: Path) -> None:
    _write_jsonl(tmp_path / "kb_chunks.jsonl", KB_CHUNKS)
    retriever = TfidfRetriever.from_chunk_store(data_dir=str(tmp_path))

    filtered_results = retriever.retrieve("补贴 合作社", top_k=2, region="anhui")
    empty_results = retriever.retrieve("补贴 合作社", top_k=2, region="sichuan")

    assert len(filtered_results) == 1
    assert filtered_results[0].chunk.chunk_id == "doc-2:0"
    assert empty_results == []



def test_tokenizer_keeps_useful_cjk_terms() -> None:
    tokens = tokenize_for_retrieval("贴息贷款支持生猪养殖")

    assert "贴息贷款" in tokens
    assert "生猪养殖" in tokens
    assert "贷款" in tokens
