"""Parser registry and file-type-based dispatch for ingestion."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from src.common.enums import FileType, ParseStatus, TextQualityFlag
from src.common.schemas import ManifestRecord, ParseResult, SourceDocument
from src.parsers import parse_docx

ParserFunc = Callable[[ManifestRecord], ParseResult]
PDF_TEXT_PATTERN = re.compile(rb"\(([^()]*)\)")


@dataclass(slots=True)
class ParserRegistry:
    """Mutable parser registry keyed by file type."""

    _parsers: dict[FileType, ParserFunc]

    def register(self, file_type: FileType, parser: ParserFunc) -> None:
        self._parsers[file_type] = parser

    def get(self, file_type: FileType) -> ParserFunc | None:
        return self._parsers.get(file_type)


def build_default_registry() -> ParserRegistry:
    registry = ParserRegistry(_parsers={})
    registry.register(FileType.DOCX, _parse_docx)
    registry.register(FileType.TXT, _parse_text)
    registry.register(FileType.MD, _parse_text)
    registry.register(FileType.HTML, _parse_text)
    registry.register(FileType.PDF, _parse_pdf)
    return registry


def parse_document(record: ManifestRecord, registry: ParserRegistry | None = None) -> ParseResult:
    """Parse a manifest record into a normalized document via the registry."""

    active_registry = registry or build_default_registry()
    parser = active_registry.get(record.file_type)
    if parser is None:
        return _failed_result(record, f"No parser registered for file type: {record.file_type}")

    try:
        result = parser(record)
    except Exception as exc:  # noqa: BLE001
        return _failed_result(record, f"Unexpected parser error: {exc}")

    return result


def _parse_docx(record: ManifestRecord) -> ParseResult:
    return parse_docx(record)


def _parse_text(record: ManifestRecord) -> ParseResult:
    path = Path(record.source_path)
    raw_text = path.read_text(encoding="utf-8", errors="ignore")
    paragraphs = [line.strip() for line in raw_text.splitlines() if line.strip()]
    status = ParseStatus.SUCCESS if raw_text.strip() else ParseStatus.PARTIAL
    quality = TextQualityFlag.CLEAN if raw_text.strip() else TextQualityFlag.EMPTY

    document = SourceDocument(
        doc_id=record.doc_id,
        region=record.region,
        source_path=record.source_path,
        file_name=record.file_name,
        file_type=record.file_type,
        title=paragraphs[0] if paragraphs else path.stem,
        raw_text=raw_text,
        paragraphs=paragraphs,
        parse_status=status,
        parse_error=None,
        source_format_confidence=0.8,
        text_quality_flag=quality,
        needs_manual_review=status is not ParseStatus.SUCCESS,
        ocr_needed=False,
        ingestion_time=datetime.now(timezone.utc),
    )
    return ParseResult(document=document, success=status is ParseStatus.SUCCESS, warnings=[], parser_name="text_parser")


def _parse_pdf(record: ManifestRecord) -> ParseResult:
    path = Path(record.source_path)
    raw_bytes = path.read_bytes()
    extracted_fragments: list[str] = []

    for match in PDF_TEXT_PATTERN.findall(raw_bytes):
        fragment = match.replace(rb"\\n", b" ").replace(rb"\\r", b" ")
        decoded = fragment.decode("utf-8", errors="ignore").strip()
        if len(decoded) >= 2:
            extracted_fragments.append(decoded)

    raw_text = "\n".join(extracted_fragments)
    unique_fragments = []
    seen: set[str] = set()
    for fragment in extracted_fragments:
        if fragment not in seen:
            unique_fragments.append(fragment)
            seen.add(fragment)

    if raw_text.strip():
        status = ParseStatus.PARTIAL
        parse_error = "PDF parsed with fallback extractor; verify formatting if needed."
        quality = TextQualityFlag.LOW_CONFIDENCE
        needs_manual_review = True
        ocr_needed = False
        warnings = [parse_error]
    else:
        status = ParseStatus.FAILED
        parse_error = "PDF text extraction unavailable with the current standard-library parser."
        quality = TextQualityFlag.NEEDS_REVIEW
        needs_manual_review = True
        ocr_needed = True
        warnings = [parse_error]

    document = SourceDocument(
        doc_id=record.doc_id,
        region=record.region,
        source_path=record.source_path,
        file_name=record.file_name,
        file_type=record.file_type,
        title=path.stem,
        raw_text=raw_text,
        paragraphs=unique_fragments,
        parse_status=status,
        parse_error=parse_error,
        source_format_confidence=0.35 if raw_text.strip() else 0.0,
        text_quality_flag=quality,
        needs_manual_review=needs_manual_review,
        ocr_needed=ocr_needed,
        ingestion_time=datetime.now(timezone.utc),
    )
    return ParseResult(document=document, success=status is not ParseStatus.FAILED, warnings=warnings, parser_name="pdf_fallback_parser")


def _failed_result(record: ManifestRecord, error: str) -> ParseResult:
    document = SourceDocument(
        doc_id=record.doc_id,
        region=record.region,
        source_path=record.source_path,
        file_name=record.file_name,
        file_type=record.file_type,
        title=Path(record.file_name).stem,
        raw_text="",
        paragraphs=[],
        parse_status=ParseStatus.FAILED,
        parse_error=error,
        source_format_confidence=0.0,
        text_quality_flag=TextQualityFlag.NEEDS_REVIEW,
        needs_manual_review=True,
        ocr_needed=record.file_type is FileType.PDF,
        ingestion_time=datetime.now(timezone.utc),
    )
    return ParseResult(document=document, success=False, warnings=[error], parser_name="unavailable_parser")


__all__ = ["ParserRegistry", "build_default_registry", "parse_document"]
