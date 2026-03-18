"""FastAPI application that orchestrates the fixed rural-credit QA pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from src.econ.econ_adapter import adapt_econ_result
from src.evidence.sentence_selector import select_evidence_sentences
from src.extract.parameter_parser import parse_extracted_parameters
from src.memory import DEFAULT_SESSION_STORE, SessionStateStore, update_session_state
from src.normalize import QueryNormalizer
from src.response import build_structured_response
from src.retrieve.bm25_retriever import BM25Retriever

PIPELINE_STEPS = [
    "query_normalizer",
    "retriever",
    "evidence_selector",
    "parameter_extraction",
    "econ_adapter",
    "session_update",
    "response_builder",
]


@dataclass(slots=True)
class QueryPipeline:
    """Container for the fixed-order QA pipeline dependencies."""

    normalizer: QueryNormalizer
    session_store: SessionStateStore
    data_dir: Path | None = None
    chunk_path: Path | None = None
    retriever: BM25Retriever | None = None
    kb_status: str = "not_loaded"
    kb_error: str | None = None

    def load_kb(self) -> None:
        """Load or reload the retrieval index without rebuilding the data artifacts."""

        try:
            self.retriever = BM25Retriever.from_chunk_store(
                data_dir=str(self.data_dir) if self.data_dir else None,
                chunk_path=str(self.chunk_path) if self.chunk_path else None,
            )
            self.kb_status = "loaded"
            self.kb_error = None
        except FileNotFoundError as exc:
            self.retriever = None
            self.kb_status = "missing"
            self.kb_error = str(exc)

    def answer(self, *, session_id: str, raw_query: str) -> dict[str, Any]:
        """Run the application pipeline in the required fixed order."""

        query = raw_query.strip()
        if not query:
            raise ValueError("query/user_query must not be empty")

        # 1) query normalizer
        normalized = self.normalizer.normalize_query(query)
        normalized_query = normalized["normalized_query"] or query

        # 2) retriever
        session_state = self.session_store.get_or_create(session_id)
        region = session_state.current_region
        retrieved_chunks = (
            self.retriever.retrieve(normalized_query, top_k=5, region=region)
            if self.retriever is not None
            else []
        )

        # 3) evidence selector
        selected_evidence = select_evidence_sentences(
            normalized_query,
            retrieved_chunks,
            top_k_chunks=3,
            max_sentences=3,
        )

        # 4) parameter extraction
        extracted_parameters = _extract_parameters(selected_evidence, retrieved_chunks)

        # 5) econ adapter
        econ_result = adapt_econ_result(extracted_parameters)

        # 6) session update
        updated_session_state = update_session_state(
            session_id=session_id,
            query=query,
            evidence=selected_evidence,
            store=self.session_store,
        )

        # 7) response builder
        response = build_structured_response(
            normalized_query=normalized_query,
            retrieved_chunks=retrieved_chunks,
            selected_evidence=selected_evidence,
            extracted_parameters=extracted_parameters,
            econ_result=econ_result,
            session_state=updated_session_state,
        )

        trace = response["trace"]
        return {
            "session_id": session_id,
            "original_query": query,
            "normalized_query": normalized_query,
            "normalization_trace": normalized["normalization_trace"],
            "detected_terms": normalized["detected_terms"],
            "pipeline_steps": list(PIPELINE_STEPS),
            "retrieved_chunks": trace["retrieved_chunks"],
            "selected_evidence": trace["selected_evidence"],
            "selected_sentences": trace["selected_evidence"],
            "extracted_parameters": trace["extracted_parameters"],
            "econ_result": trace["econ_result"],
            "session_state": response["session_state"],
            "summary": response["summary"],
            "citations": response["citations"],
            "uncertainty": response["uncertainty"],
            "final_response": response["final_response"],
        }


def create_app(
    *,
    data_dir: str | Path | None = None,
    chunk_path: str | Path | None = None,
    session_store: SessionStateStore | None = None,
) -> FastAPI:
    """Create the HTTP application with injectable local dependencies for tests."""

    app = FastAPI(title="argecon api", version="0.1.0")
    pipeline = QueryPipeline(
        normalizer=QueryNormalizer(),
        session_store=session_store or DEFAULT_SESSION_STORE,
        data_dir=Path(data_dir) if data_dir else None,
        chunk_path=Path(chunk_path) if chunk_path else None,
    )
    pipeline.load_kb()
    app.state.pipeline = pipeline

    @app.get("/health")
    async def health() -> dict[str, Any]:
        active_pipeline: QueryPipeline = app.state.pipeline
        return {
            "status": "ok",
            "service": "argecon-api",
            "kb_status": active_pipeline.kb_status,
            "kb_error": active_pipeline.kb_error,
        }

    @app.post("/query")
    async def query_endpoint(request: Request) -> dict[str, Any]:
        return await _handle_query_request(request)

    @app.post("/ask")
    async def ask_endpoint(request: Request) -> dict[str, Any]:
        return await _handle_query_request(request)

    if _dev_endpoints_enabled():

        @app.post("/reload_kb")
        async def reload_kb() -> dict[str, Any]:
            active_pipeline: QueryPipeline = app.state.pipeline
            active_pipeline.load_kb()
            return {
                "status": "ok",
                "kb_status": active_pipeline.kb_status,
                "kb_error": active_pipeline.kb_error,
            }

    async def _handle_query_request(request: Request) -> dict[str, Any]:
        payload = await request.json()
        session_id = _coerce_text(payload.get("session_id"))
        raw_query = _coerce_text(payload.get("query")) or _coerce_text(payload.get("user_query"))

        if not session_id:
            raise HTTPException(status_code=422, detail="session_id is required")
        if not raw_query:
            raise HTTPException(status_code=422, detail="query or user_query is required")

        try:
            return app.state.pipeline.answer(session_id=session_id, raw_query=raw_query)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app


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


def _coerce_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _dev_endpoints_enabled() -> bool:
    return os.getenv("ARGE_CON_ENABLE_DEV_ENDPOINTS", "1").strip().lower() not in {"0", "false", "no"}


app = create_app()


__all__ = ["PIPELINE_STEPS", "QueryPipeline", "app", "create_app"]
