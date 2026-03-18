"""Image parser stub that advertises OCR-required status without crashing ingestion."""

from __future__ import annotations

from pathlib import Path

from src.common.enums import ParseStatus, TextQualityFlag
from src.common.schemas import ManifestRecord, ParseResult
from src.parsers.base import ParseDiagnostics, build_parse_result


def parse_image(record: ManifestRecord) -> ParseResult:
    """Return a placeholder result for image files until OCR support is added."""

    message = "Image OCR is not implemented yet; file detected and deferred for OCR/manual review."
    return build_parse_result(
        record=record,
        parser_name="image_parser",
        title=Path(record.file_name).stem,
        raw_text="",
        paragraphs=[],
        diagnostics=ParseDiagnostics(
            status=ParseStatus.SKIPPED,
            parse_error=message,
            text_quality_flag=TextQualityFlag.NEEDS_REVIEW,
            source_format_confidence=0.0,
            needs_manual_review=True,
            ocr_needed=True,
            warnings=[message],
        ),
    )


__all__ = ["parse_image"]
