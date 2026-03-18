"""Markdown parser with lightweight heading-aware segmentation."""

from __future__ import annotations

from src.common.enums import ParseStatus, TextQualityFlag
from src.common.schemas import ManifestRecord, ParseResult
from src.parsers.base import ParseDiagnostics, build_parse_result, parse_plain_text_payload


def parse_md(record: ManifestRecord) -> ParseResult:
    """Parse `.md` files into the shared document structure."""

    payload = parse_plain_text_payload(record.source_path, markdown=True)
    has_text = bool(payload.raw_text.strip())
    diagnostics = ParseDiagnostics(
        status=ParseStatus.SUCCESS if has_text else ParseStatus.PARTIAL,
        parse_error=None if has_text else "Markdown file is empty after decoding.",
        text_quality_flag=TextQualityFlag.CLEAN if has_text else TextQualityFlag.EMPTY,
        source_format_confidence=0.9 if has_text else 0.25,
        needs_manual_review=not has_text,
        warnings=[] if has_text else ["Markdown file is empty after decoding."],
    )
    return build_parse_result(
        record=record,
        parser_name="md_parser",
        title=payload.title,
        raw_text=payload.raw_text,
        paragraphs=payload.paragraphs,
        diagnostics=diagnostics,
    )


__all__ = ["parse_md"]
