"""Local demo entrypoint for querying the retrieval-and-response pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.econ.econ_adapter import adapt_econ_result
from src.evidence.sentence_selector import select_evidence_sentences
from src.extract.parameter_parser import parse_extracted_parameters
from src.memory import DEFAULT_SESSION_STORE, update_session_state
from src.normalize import QueryNormalizer
from src.response import build_structured_response
from src.retrieve.bm25_retriever import BM25Retriever


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="本地演示：加载 chunks 后直接运行问答链路。")
    parser.add_argument("query", help="用户查询")
    parser.add_argument("--session-id", default="demo-session", help="演示 session_id")
    parser.add_argument("--data-dir", default="data/processed", help="chunk 产物目录")
    parser.add_argument("--chunk-path", default=None, help="显式指定 chunk 文件")
    parser.add_argument("--region", default=None, help="为 demo session 预设地区")
    parser.add_argument("--pretty", action="store_true", help="输出完整 JSON 结果")
    return parser


def build_retriever(*, data_dir: str | Path, chunk_path: str | Path | None = None) -> BM25Retriever:
    return BM25Retriever.from_chunk_store(
        data_dir=str(data_dir),
        chunk_path=str(chunk_path) if chunk_path else None,
    )


def _extract_parameters(selected_evidence: list[Any], retrieved_chunks: list[Any]) -> Any:
    if not selected_evidence:
        return None

    first_evidence = selected_evidence[0]
    chunk_lookup = {item.chunk.chunk_id: item.chunk for item in retrieved_chunks}
    chunk = chunk_lookup.get(first_evidence.chunk_id)
    chunk_metadata = None

    if chunk is not None:
        chunk_metadata = {
            "chunk_text": chunk.chunk_text,
            "section_title": chunk.section_title,
            "source_title": chunk.source_title,
            "metadata": dict(chunk.metadata),
        }

    return parse_extracted_parameters(first_evidence.evidence_text, chunk_metadata)


def answer_query(
    *,
    retriever: BM25Retriever,
    normalizer: QueryNormalizer,
    session_id: str,
    raw_query: str,
) -> dict[str, Any]:
    normalized = normalizer.normalize_query(raw_query)
    normalized_query = normalized["normalized_query"] or raw_query.strip()
    session_state = DEFAULT_SESSION_STORE.get_or_create(session_id)
    retrieved_chunks = retriever.retrieve(normalized_query, top_k=5, region=session_state.current_region)
    selected_evidence = select_evidence_sentences(
        normalized_query,
        retrieved_chunks,
        top_k_chunks=3,
        max_sentences=3,
    )
    extracted_parameters = _extract_parameters(selected_evidence, retrieved_chunks)
    econ_result = adapt_econ_result(extracted_parameters)
    updated_session_state = update_session_state(
        session_id=session_id,
        query=raw_query,
        evidence=selected_evidence,
        store=DEFAULT_SESSION_STORE,
    )
    response = build_structured_response(
        normalized_query=normalized_query,
        retrieved_chunks=retrieved_chunks,
        selected_evidence=selected_evidence,
        extracted_parameters=extracted_parameters,
        econ_result=econ_result,
        session_state=updated_session_state,
    )
    return {
        "session_id": session_id,
        "original_query": raw_query,
        "normalized_query": normalized_query,
        "normalization_trace": normalized["normalization_trace"],
        "detected_terms": normalized["detected_terms"],
        "summary": response["summary"],
        "citations": response["citations"],
        "uncertainty": response["uncertainty"],
        "final_response": response["final_response"],
        "trace": response["trace"],
    }


def run_cli(args: argparse.Namespace) -> dict[str, object]:
    DEFAULT_SESSION_STORE.clear()
    session_state = DEFAULT_SESSION_STORE.get_or_create(args.session_id)
    if args.region:
        session_state.current_region = args.region

    response = answer_query(
        retriever=build_retriever(data_dir=args.data_dir, chunk_path=args.chunk_path),
        normalizer=QueryNormalizer(),
        session_id=args.session_id,
        raw_query=args.query,
    )
    if args.pretty:
        print(json.dumps(response, ensure_ascii=False, indent=2))
    else:
        print(response["final_response"])
    return response


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    run_cli(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
