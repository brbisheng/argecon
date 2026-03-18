from __future__ import annotations

import json

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.memory.session_state import SessionStateStore


def _write_chunk(path: str) -> None:
    payload = {
        "chunk_id": "doc-1:0",
        "doc_id": "doc-1",
        "region": "beijing",
        "source_title": "农业生产资料贷款办法",
        "chunk_index": 0,
        "chunk_text": "购买化肥、种子等农业生产资料可申请贷款，贷款额度最高50万元，期限12个月，并给予贴息支持。",
        "section_title": "支持范围",
        "metadata": {},
    }
    with open(path, "w", encoding="utf-8") as file_obj:
        file_obj.write(json.dumps(payload, ensure_ascii=False) + "\n")


def test_health_endpoint_reports_service_status(tmp_path) -> None:
    chunk_path = tmp_path / "kb_chunks.jsonl"
    _write_chunk(str(chunk_path))
    app = create_app(chunk_path=chunk_path, session_store=SessionStateStore())

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["kb_status"] == "loaded"


def test_query_endpoint_runs_fixed_pipeline_and_returns_structured_payload(tmp_path) -> None:
    chunk_path = tmp_path / "kb_chunks.jsonl"
    _write_chunk(str(chunk_path))
    app = create_app(chunk_path=chunk_path, session_store=SessionStateStore())

    client = TestClient(app)
    response = client.post(
        "/query",
        json={"session_id": "sess-1", "user_query": "我想贷款买化肥，额度和期限是什么？"},
    )

    payload = response.json()

    assert response.status_code == 200
    assert payload["pipeline_steps"] == [
        "query_normalizer",
        "retriever",
        "evidence_selector",
        "parameter_extraction",
        "econ_adapter",
        "session_update",
        "response_builder",
    ]
    assert payload["normalized_query"]
    assert payload["retrieved_chunks"]
    assert payload["selected_evidence"]
    assert payload["selected_sentences"] == payload["selected_evidence"]
    assert payload["extracted_parameters"]["loan_amount_upper_limit"] == 500000.0
    assert payload["extracted_parameters"]["loan_term_months"] == 12
    assert payload["econ_result"] is not None
    assert "50" in payload["final_response"]


def test_ask_endpoint_accepts_query_alias_and_updates_session_state(tmp_path) -> None:
    chunk_path = tmp_path / "kb_chunks.jsonl"
    _write_chunk(str(chunk_path))
    app = create_app(chunk_path=chunk_path, session_store=SessionStateStore())

    client = TestClient(app)
    response = client.post(
        "/ask",
        json={"session_id": "sess-2", "query": "我不是合作社，想贷10万元买化肥。"},
    )

    payload = response.json()

    assert response.status_code == 200
    assert payload["session_state"]["session_id"] == "sess-2"
    assert payload["session_state"]["cooperative"] is False
    assert payload["session_state"]["amount"] == "10万元"


def test_query_endpoint_requires_session_id_and_query(tmp_path) -> None:
    chunk_path = tmp_path / "kb_chunks.jsonl"
    _write_chunk(str(chunk_path))
    app = create_app(chunk_path=chunk_path, session_store=SessionStateStore())

    client = TestClient(app)
    response = client.post("/query", json={"query": "我想贷款"})

    assert response.status_code == 422
    assert "session_id" in response.json()["detail"]
