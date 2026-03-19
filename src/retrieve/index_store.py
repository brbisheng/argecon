"""Chunk loading and lexical index building entrypoints for retrieval."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from src.common import ChunkRecord

_DEFAULT_CHUNK_FILES = (("chunks", "kb_chunks.jsonl"), ("chunks", "chunks.jsonl"), ("kb_chunks.jsonl",), ("chunks.jsonl",))
_TOKEN_SPLIT_RE = re.compile(r"[\s\W_]+", re.UNICODE)
_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")


@dataclass(slots=True)
class ChunkIndex:
    """In-memory lexical index shared by different retrievers."""

    chunks: list[ChunkRecord]
    chunk_lookup: dict[str, ChunkRecord]
    tokenized_chunks: list[list[str]]
    term_frequencies: list[Counter[str]]
    document_frequencies: dict[str, int]
    document_lengths: list[int]
    average_document_length: float
    metadata: dict[str, Any]


class ChunkIndexStore:
    """Load chunk data and build a reusable lexical index."""

    def __init__(self, *, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else _default_data_dir()

    def resolve_chunk_path(self, chunk_path: str | Path | None = None) -> Path:
        """Resolve an explicit chunk file or discover a preferred default artifact."""

        if chunk_path is not None:
            candidate = Path(chunk_path)
            if not candidate.is_absolute():
                candidate = self.data_dir / candidate
            if not candidate.exists():
                raise FileNotFoundError(f"Chunk file not found: {candidate}")
            return candidate

        for path_parts in _DEFAULT_CHUNK_FILES:
            candidate = self.data_dir.joinpath(*path_parts)
            if candidate.exists() and candidate.stat().st_size > 0:
                return candidate

        for path_parts in _DEFAULT_CHUNK_FILES:
            candidate = self.data_dir.joinpath(*path_parts)
            if candidate.exists():
                return candidate

        searched = ", ".join(str(self.data_dir.joinpath(*path_parts)) for path_parts in _DEFAULT_CHUNK_FILES)
        raise FileNotFoundError(f"No chunk artifact found. Looked for: {searched}")

    def load_chunks(self, chunk_path: str | Path | None = None) -> list[ChunkRecord]:
        """Load chunk records from canonical chunks.jsonl or KB-oriented kb_chunks.jsonl."""

        resolved_path = self.resolve_chunk_path(chunk_path)
        chunks: list[ChunkRecord] = []
        with resolved_path.open("r", encoding="utf-8") as file_obj:
            for line_number, raw_line in enumerate(file_obj, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                try:
                    chunks.append(_chunk_record_from_payload(payload))
                except Exception as exc:  # pragma: no cover - defensive context wrapper
                    raise ValueError(f"Invalid chunk payload at {resolved_path}:{line_number}") from exc
        return chunks

    def build_index(
        self,
        chunks: Sequence[ChunkRecord] | None = None,
        *,
        chunk_path: str | Path | None = None,
    ) -> ChunkIndex:
        """Build a lexical index with term/document statistics for retrieval."""

        chunk_records = list(chunks) if chunks is not None else self.load_chunks(chunk_path)
        tokenized_chunks = [tokenize_for_retrieval(chunk.chunk_text) for chunk in chunk_records]
        term_frequencies = [Counter(tokens) for tokens in tokenized_chunks]

        document_frequencies: dict[str, int] = defaultdict(int)
        for tokens in tokenized_chunks:
            for token in set(tokens):
                document_frequencies[token] += 1

        document_lengths = [len(tokens) for tokens in tokenized_chunks]
        average_document_length = (
            sum(document_lengths) / len(document_lengths) if document_lengths else 0.0
        )

        return ChunkIndex(
            chunks=chunk_records,
            chunk_lookup={chunk.chunk_id: chunk for chunk in chunk_records},
            tokenized_chunks=tokenized_chunks,
            term_frequencies=term_frequencies,
            document_frequencies=dict(document_frequencies),
            document_lengths=document_lengths,
            average_document_length=average_document_length,
            metadata={
                "chunk_count": len(chunk_records),
                "source_path": str(self.resolve_chunk_path(chunk_path)) if chunks is None else None,
            },
        )


def load_chunk_index(
    *,
    data_dir: str | Path | None = None,
    chunk_path: str | Path | None = None,
) -> ChunkIndex:
    """Convenience entrypoint used by retrievers and future pipelines."""

    return ChunkIndexStore(data_dir=data_dir).build_index(chunk_path=chunk_path)


def serialize_chunk_index(index: ChunkIndex) -> dict[str, Any]:
    """Convert a built chunk index into a stable JSON-serializable payload."""

    return {
        "metadata": dict(index.metadata),
        "chunks": [asdict(chunk) for chunk in index.chunks],
        "tokenized_chunks": [list(tokens) for tokens in index.tokenized_chunks],
        "term_frequencies": [dict(counter) for counter in index.term_frequencies],
        "document_frequencies": dict(index.document_frequencies),
        "document_lengths": list(index.document_lengths),
        "average_document_length": index.average_document_length,
    }


def save_chunk_index(index: ChunkIndex, output_path: str | Path) -> Path:
    """Persist a built chunk index as JSON for offline inspection/debugging."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(serialize_chunk_index(index), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destination


def tokenize_for_retrieval(text: str) -> list[str]:
    """Produce lightweight lexical tokens that work for Chinese and Latin text."""

    normalized = text.casefold().strip()
    if not normalized:
        return []

    tokens: list[str] = []

    for piece in _TOKEN_SPLIT_RE.split(normalized):
        if not piece:
            continue
        if _CJK_RE.fullmatch(piece):
            tokens.extend(_cjk_terms(piece))
        elif len(piece) > 1:
            tokens.append(piece)

    for cjk_span in _CJK_RE.findall(normalized):
        tokens.extend(_cjk_terms(cjk_span))

    return _dedupe_preserve_order(tokens)


def _cjk_terms(text: str) -> list[str]:
    if not text:
        return []

    terms: list[str] = []
    if len(text) <= 8:
        terms.append(text)

    max_n = min(4, len(text))
    for ngram_size in range(2, max_n + 1):
        for index in range(0, len(text) - ngram_size + 1):
            terms.append(text[index : index + ngram_size])
    if len(text) == 1:
        terms.append(text)
    return terms


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _chunk_record_from_payload(payload: dict[str, Any]) -> ChunkRecord:
    metadata = dict(payload.get("metadata") or {})
    for field_name in ("source_path", "source_type", "policy_type", "effective_date", "tags", "econ_metadata"):
        if field_name in payload and field_name not in metadata:
            metadata[field_name] = payload[field_name]

    paragraph_range = payload.get("paragraph_range")
    if isinstance(paragraph_range, list):
        paragraph_range = tuple(paragraph_range)

    chunk_text = (
        payload.get("chunk_text")
        or payload.get("text")
        or payload.get("content")
        or ""
    )
    source_title = payload.get("source_title") or payload.get("title") or ""

    return ChunkRecord(
        chunk_id=str(payload["chunk_id"]),
        doc_id=str(payload.get("doc_id") or payload.get("document_id") or payload["chunk_id"]),
        region=str(payload.get("region") or metadata.get("region") or ""),
        source_title=str(source_title),
        chunk_text=str(chunk_text),
        chunk_index=int(payload.get("chunk_index") or payload.get("index") or 0),
        section_title=payload.get("section_title") or payload.get("section"),
        page_no=payload.get("page_no"),
        paragraph_range=paragraph_range,
        metadata=metadata,
    )


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "processed"


__all__ = [
    "ChunkIndex",
    "ChunkIndexStore",
    "load_chunk_index",
    "save_chunk_index",
    "serialize_chunk_index",
    "tokenize_for_retrieval",
]
