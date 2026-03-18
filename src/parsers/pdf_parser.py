"""Basic parser for text-layer PDFs using a conservative standard-library extractor."""

from __future__ import annotations

import re
from pathlib import Path

from src.common.enums import ParseStatus, TextQualityFlag
from src.common.schemas import ManifestRecord, ParseResult
from src.parsers.base import ParseDiagnostics, build_parse_result

PDF_TEXT_PATTERN = re.compile(rb"\(([^()]*)\)")
MIN_EXTRACTED_CHARACTERS = 80
MIN_PARAGRAPHS = 2


def parse_pdf(record: ManifestRecord) -> ParseResult:
    """Parse a text-extractable PDF; flag suspected scanned/broken PDFs for OCR."""

    path = Path(record.source_path)
    raw_bytes = path.read_bytes()
    fragments: list[str] = []

    for match in PDF_TEXT_PATTERN.findall(raw_bytes):
        fragment = match.replace(rb"\\n", b" ").replace(rb"\\r", b" ").replace(rb"\\t", b" ")
        decoded = fragment.decode("utf-8", errors="ignore").strip()
        normalized = " ".join(decoded.split())
        if len(normalized) >= 2:
            fragments.append(normalized)

    paragraphs = _deduplicate_fragments(fragments)
    raw_text = "\n".join(paragraphs)
    diagnostics = _classify_pdf_parse(raw_text=raw_text, paragraphs=paragraphs)

    return build_parse_result(
        record=record,
        parser_name="pdf_parser",
        title=path.stem,
        raw_text=raw_text,
        paragraphs=paragraphs,
        diagnostics=diagnostics,
    )


def _deduplicate_fragments(fragments: list[str]) -> list[str]:
    deduplicated: list[str] = []
    seen: set[str] = set()
    for fragment in fragments:
        if fragment in seen:
            continue
        deduplicated.append(fragment)
        seen.add(fragment)
    return deduplicated


def _classify_pdf_parse(*, raw_text: str, paragraphs: list[str]) -> ParseDiagnostics:
    if not raw_text.strip():
        message = "PDF has no extractable text; OCR support is required."
        return ParseDiagnostics(
            status=ParseStatus.FAILED,
            parse_error=message,
            text_quality_flag=TextQualityFlag.EMPTY,
            source_format_confidence=0.0,
            needs_manual_review=True,
            ocr_needed=True,
            warnings=[message],
        )

    if len(raw_text.strip()) < MIN_EXTRACTED_CHARACTERS or len(paragraphs) < MIN_PARAGRAPHS:
        message = "PDF text extraction produced too little or too little structure; OCR/manual review recommended."
        return ParseDiagnostics(
            status=ParseStatus.PARTIAL,
            parse_error=message,
            text_quality_flag=TextQualityFlag.LOW_CONFIDENCE,
            source_format_confidence=0.35,
            needs_manual_review=True,
            ocr_needed=True,
            warnings=[message],
        )

    return ParseDiagnostics(
        status=ParseStatus.SUCCESS,
        parse_error=None,
        text_quality_flag=TextQualityFlag.LOW_CONFIDENCE,
        source_format_confidence=0.65,
        needs_manual_review=False,
        ocr_needed=False,
        warnings=["PDF text extracted via basic parser; layout and reading order may be imperfect."],
    )


__all__ = ["parse_pdf"]
