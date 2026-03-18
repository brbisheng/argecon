"""DOCX parser that normalizes Word documents into shared document schemas."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

from src.common.enums import ParseStatus, TextQualityFlag
from src.common.schemas import ManifestRecord, ParseResult, SourceDocument

WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DRAWING_NAMESPACE = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
PICTURE_NAMESPACE = "{http://schemas.openxmlformats.org/drawingml/2006/picture}"
TITLE_STYLE_KEYWORDS = ("title", "subtitle", "heading")
HEADING_TEXT_RE = re.compile(r"^[第（一二三四五六七八九十0-9IVXivx]+[章节条部分篇]\s*")
FULLWIDTH_HEADING_RE = re.compile(r"^[一二三四五六七八九十]+、")
TITLE_TRAILING_PUNCTUATION = "。；;！？!?：:，,"
MAX_TITLE_LENGTH = 80


@dataclass(slots=True)
class _ParagraphCandidate:
    text: str
    style: str | None = None
    is_first_non_empty: bool = False


@dataclass(slots=True)
class _DocxParseState:
    status: ParseStatus
    parse_error: str | None
    text_quality_flag: TextQualityFlag
    needs_manual_review: bool
    source_format_confidence: float
    warnings: list[str]
    ocr_needed: bool = False


def parse_docx(record: ManifestRecord) -> ParseResult:
    """Parse a `.docx` file into a normalized :class:`ParseResult`."""

    path = Path(record.source_path)

    try:
        with zipfile.ZipFile(path) as archive:
            try:
                with archive.open("word/document.xml") as document_xml:
                    root = ElementTree.parse(document_xml).getroot()
            except KeyError as exc:
                raise ValueError("DOCX missing word/document.xml") from exc
    except (OSError, ValueError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        error = f"DOCX parse failed: {exc}"
        return _build_result(
            record=record,
            title=path.stem,
            paragraphs=[],
            raw_text="",
            status=ParseStatus.FAILED,
            parse_error=error,
            text_quality_flag=TextQualityFlag.NEEDS_REVIEW,
            needs_manual_review=True,
            source_format_confidence=0.0,
            warnings=[error],
        )

    paragraph_candidates = _extract_paragraph_candidates(root)
    paragraphs = [candidate.text for candidate in paragraph_candidates]
    raw_text = "\n".join(paragraphs)
    title = _select_title(paragraph_candidates, path.stem)
    parse_state = _classify_docx_parse(root=root, paragraphs=paragraphs)

    return _build_result(
        record=record,
        title=title,
        paragraphs=paragraphs,
        raw_text=raw_text,
        status=parse_state.status,
        parse_error=parse_state.parse_error,
        text_quality_flag=parse_state.text_quality_flag,
        needs_manual_review=parse_state.needs_manual_review,
        source_format_confidence=parse_state.source_format_confidence,
        warnings=parse_state.warnings,
        ocr_needed=parse_state.ocr_needed,
    )


def _extract_paragraph_candidates(root: ElementTree.Element) -> list[_ParagraphCandidate]:
    candidates: list[_ParagraphCandidate] = []

    for paragraph in root.iterfind(f".//{WORD_NAMESPACE}p"):
        texts = [node.text or "" for node in paragraph.iterfind(f".//{WORD_NAMESPACE}t")]
        merged = "".join(texts)
        normalized = "\n".join(part.strip() for part in merged.splitlines() if part.strip()).strip()
        if not normalized:
            continue

        style = None
        style_node = paragraph.find(f"./{WORD_NAMESPACE}pPr/{WORD_NAMESPACE}pStyle")
        if style_node is not None:
            style = style_node.attrib.get(f"{WORD_NAMESPACE}val")

        candidates.append(
            _ParagraphCandidate(
                text=normalized,
                style=style.lower() if style else None,
                is_first_non_empty=not candidates,
            )
        )

    return candidates


def _select_title(paragraphs: list[_ParagraphCandidate], fallback: str) -> str:
    if not paragraphs:
        return fallback

    first = paragraphs[0]
    if _is_main_title(first):
        return first.text

    for paragraph in paragraphs:
        if _is_high_confidence_title(paragraph):
            return paragraph.text

    return first.text or fallback


def _is_main_title(paragraph: _ParagraphCandidate) -> bool:
    if paragraph.style and any(keyword in paragraph.style for keyword in TITLE_STYLE_KEYWORDS):
        return True
    return paragraph.is_first_non_empty and _looks_like_title_text(paragraph.text, allow_relaxed_length=True)


def _is_high_confidence_title(paragraph: _ParagraphCandidate) -> bool:
    if paragraph.style and any(keyword in paragraph.style for keyword in TITLE_STYLE_KEYWORDS):
        return True
    return _looks_like_title_text(paragraph.text, allow_relaxed_length=False)


def _looks_like_title_text(text: str, *, allow_relaxed_length: bool) -> bool:
    stripped = text.strip()
    if not stripped:
        return False

    max_length = 120 if allow_relaxed_length else MAX_TITLE_LENGTH
    if len(stripped) > max_length:
        return False
    if stripped.endswith(tuple(TITLE_TRAILING_PUNCTUATION)):
        return False
    if "\n" in stripped:
        return False
    if HEADING_TEXT_RE.match(stripped) or FULLWIDTH_HEADING_RE.match(stripped):
        return True

    has_sentence_marker = any(marker in stripped for marker in ("。", "；", ";", "？", "!", "！"))
    if has_sentence_marker:
        return False

    return True


def _classify_docx_parse(root: ElementTree.Element, paragraphs: list[str]) -> _DocxParseState:
    if paragraphs:
        return _DocxParseState(
            status=ParseStatus.SUCCESS,
            parse_error=None,
            text_quality_flag=TextQualityFlag.CLEAN,
            needs_manual_review=False,
            source_format_confidence=0.95,
            warnings=[],
        )

    has_visual_content = any(root.iterfind(f".//{WORD_NAMESPACE}drawing")) or any(
        root.iterfind(f".//{DRAWING_NAMESPACE}blip")
    )
    has_embedded_object = any(root.iterfind(f".//{WORD_NAMESPACE}object")) or any(
        root.iterfind(f".//{PICTURE_NAMESPACE}pic")
    )

    if has_visual_content or has_embedded_object:
        error = "DOCX contains non-text content only; OCR or manual review may be required."
        return _DocxParseState(
            status=ParseStatus.PARTIAL,
            parse_error=error,
            text_quality_flag=TextQualityFlag.EMPTY,
            needs_manual_review=True,
            source_format_confidence=0.35,
            warnings=[error],
            ocr_needed=True,
        )

    error = "DOCX contains no extractable text paragraphs."
    return _DocxParseState(
        status=ParseStatus.PARTIAL,
        parse_error=error,
        text_quality_flag=TextQualityFlag.EMPTY,
        needs_manual_review=True,
        source_format_confidence=0.15,
        warnings=[error],
    )


def _build_result(
    *,
    record: ManifestRecord,
    title: str,
    paragraphs: list[str],
    raw_text: str,
    status: ParseStatus,
    parse_error: str | None,
    text_quality_flag: TextQualityFlag,
    needs_manual_review: bool,
    source_format_confidence: float,
    warnings: list[str],
    ocr_needed: bool = False,
) -> ParseResult:
    document = SourceDocument(
        doc_id=record.doc_id,
        region=record.region,
        source_path=record.source_path,
        file_name=record.file_name,
        file_type=record.file_type,
        title=title,
        raw_text=raw_text,
        paragraphs=paragraphs,
        parse_status=status,
        parse_error=parse_error,
        source_format_confidence=source_format_confidence,
        text_quality_flag=text_quality_flag,
        needs_manual_review=needs_manual_review,
        ocr_needed=ocr_needed,
        ingestion_time=datetime.now(timezone.utc),
    )
    return ParseResult(
        document=document,
        success=status is ParseStatus.SUCCESS,
        warnings=warnings,
        parser_name="docx_parser",
    )


__all__ = ["parse_docx"]
