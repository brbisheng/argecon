"""Shared parser contract and helpers for normalized parser output."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from src.common.enums import ParseStatus, TextQualityFlag
from src.common.schemas import ManifestRecord, ParseResult, SourceDocument

HEADING_PREFIXES = ("#", "##", "###", "####", "#####", "######")


class ParserFunc(Protocol):
    """Protocol for all format-specific parsers."""

    def __call__(self, record: ManifestRecord) -> ParseResult: ...


@dataclass(slots=True)
class ParsedTextPayload:
    """Intermediate normalized text payload shared by lightweight parsers."""

    title: str
    raw_text: str
    paragraphs: list[str]


@dataclass(slots=True)
class ParseDiagnostics:
    """Parser-level diagnostics mapped onto :class:`SourceDocument`."""

    status: ParseStatus
    parse_error: str | None
    text_quality_flag: TextQualityFlag
    source_format_confidence: float
    needs_manual_review: bool = False
    ocr_needed: bool = False
    warnings: list[str] | None = None

    def normalized_warnings(self) -> list[str]:
        return list(self.warnings or [])


def parse_plain_text_payload(path: str | Path, *, markdown: bool = False) -> ParsedTextPayload:
    """Read a UTF-8-ish text file and segment it into normalized paragraphs."""

    source_path = Path(path)
    raw_text = source_path.read_text(encoding="utf-8", errors="ignore")
    paragraphs = segment_text(raw_text, markdown=markdown)
    title = infer_title(paragraphs=paragraphs, fallback=source_path.stem)
    return ParsedTextPayload(title=title, raw_text=raw_text, paragraphs=paragraphs)


def segment_text(raw_text: str, *, markdown: bool = False) -> list[str]:
    """Split text into paragraphs using blank lines and optional heading boundaries."""

    paragraphs: list[str] = []
    buffer: list[str] = []

    def flush_buffer() -> None:
        if not buffer:
            return
        paragraph = "\n".join(part.strip() for part in buffer if part.strip()).strip()
        if paragraph:
            paragraphs.append(paragraph)
        buffer.clear()

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            flush_buffer()
            continue
        if markdown and _is_markdown_heading(stripped):
            flush_buffer()
            paragraphs.append(stripped)
            continue
        buffer.append(stripped)

    flush_buffer()
    return paragraphs


def infer_title(*, paragraphs: list[str], fallback: str) -> str:
    """Select a stable title from normalized paragraphs."""

    if not paragraphs:
        return fallback

    for paragraph in paragraphs:
        candidate = paragraph.strip()
        if not candidate:
            continue
        if _is_markdown_heading(candidate):
            return candidate.lstrip("#").strip() or fallback
        return candidate.splitlines()[0].strip() or fallback

    return fallback


def build_parse_result(
    *,
    record: ManifestRecord,
    parser_name: str,
    title: str,
    raw_text: str,
    paragraphs: list[str],
    diagnostics: ParseDiagnostics,
) -> ParseResult:
    """Construct the shared parser return structure used across all parsers."""

    document = SourceDocument(
        doc_id=record.doc_id,
        region=record.region,
        source_path=record.source_path,
        file_name=record.file_name,
        file_type=record.file_type,
        title=title,
        raw_text=raw_text,
        paragraphs=paragraphs,
        parse_status=diagnostics.status,
        parse_error=diagnostics.parse_error,
        source_format_confidence=diagnostics.source_format_confidence,
        text_quality_flag=diagnostics.text_quality_flag,
        needs_manual_review=diagnostics.needs_manual_review,
        ocr_needed=diagnostics.ocr_needed,
        ingestion_time=datetime.now(timezone.utc),
    )
    return ParseResult(
        document=document,
        success=diagnostics.status is ParseStatus.SUCCESS,
        warnings=diagnostics.normalized_warnings(),
        parser_name=parser_name,
    )


def _is_markdown_heading(text: str) -> bool:
    return any(text.startswith(prefix + " ") or text == prefix for prefix in HEADING_PREFIXES)


__all__ = [
    "ParseDiagnostics",
    "ParsedTextPayload",
    "ParserFunc",
    "build_parse_result",
    "infer_title",
    "parse_plain_text_payload",
    "segment_text",
]
