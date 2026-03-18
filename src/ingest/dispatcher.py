"""Parser registry and file-type-based dispatch for ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.common.enums import FileType, ParseStatus, TextQualityFlag
from src.common.schemas import ManifestRecord, ParseResult
from src.parsers import parse_docx, parse_image, parse_md, parse_pdf, parse_txt
from src.parsers.base import ParserFunc, build_parse_result, ParseDiagnostics


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
    registry.register(FileType.TXT, _parse_txt)
    registry.register(FileType.MD, _parse_md)
    registry.register(FileType.HTML, _parse_txt)
    registry.register(FileType.PDF, _parse_pdf)
    registry.register(FileType.IMAGE, _parse_image)
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


def _parse_txt(record: ManifestRecord) -> ParseResult:
    return parse_txt(record)


def _parse_md(record: ManifestRecord) -> ParseResult:
    return parse_md(record)


def _parse_pdf(record: ManifestRecord) -> ParseResult:
    return parse_pdf(record)


def _parse_image(record: ManifestRecord) -> ParseResult:
    return parse_image(record)


def _failed_result(record: ManifestRecord, error: str) -> ParseResult:
    return build_parse_result(
        record=record,
        parser_name="unavailable_parser",
        title=Path(record.file_name).stem,
        raw_text="",
        paragraphs=[],
        diagnostics=ParseDiagnostics(
            status=ParseStatus.FAILED,
            parse_error=error,
            text_quality_flag=TextQualityFlag.NEEDS_REVIEW,
            source_format_confidence=0.0,
            needs_manual_review=True,
            ocr_needed=record.file_type in {FileType.PDF, FileType.IMAGE},
            warnings=[error],
        ),
    )


__all__ = ["ParserRegistry", "build_default_registry", "parse_document"]
