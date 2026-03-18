"""Section and heading detection for normalized source documents."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.common.schemas import SourceDocument

_MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_CHINESE_LIST_HEADING_RE = re.compile(r"^[一二三四五六七八九十百千]+、\s*(.+)$")
_CHINESE_ARTICLE_HEADING_RE = re.compile(r"^第[一二三四五六七八九十百千0-9]+[章节条款部分编]\s*(.*)$")
_NUMERIC_HEADING_RE = re.compile(r"^(?:[(（]?[0-9]+[)）]|[0-9]+[.、])\s*(.+)$")
_SHORT_TITLE_PREFIX_RE = re.compile(r"^(?:附件|附录|说明|注：|备注：|一是|二是|三是|四是|五是|六是)\s*")
_SENTENCE_PUNCTUATION = set("。；！？;!?")
_TITLE_TRAILING_PUNCTUATION = set("。；！？;!?，,：:")
_MAX_SHORT_TITLE_LENGTH = 30


@dataclass(slots=True)
class SectionSpan:
    """A heading-aware paragraph span in a normalized source document."""

    title: str | None
    start_paragraph: int
    end_paragraph: int
    heading_paragraph: int | None = None


@dataclass(slots=True)
class SectionSplitResult:
    """Section boundaries resolved from a normalized document."""

    document: SourceDocument
    sections: list[SectionSpan]


def split_sections(document: SourceDocument) -> SectionSplitResult:
    """Detect section boundaries from document paragraphs.

    The splitter supports common Chinese policy document headings such as
    ``一、二、三`` / ``第一条`` / ``1.`` as well as markdown headings and
    short standalone title lines.
    """

    paragraphs = [paragraph.strip() for paragraph in document.paragraphs if paragraph.strip()]
    if not paragraphs:
        return SectionSplitResult(document=document, sections=[])

    sections: list[SectionSpan] = []
    current_title: str | None = None
    current_start = 0
    current_heading: int | None = None

    for index, paragraph in enumerate(paragraphs):
        if not is_section_heading(paragraph):
            continue

        if index > current_start:
            sections.append(
                SectionSpan(
                    title=current_title,
                    start_paragraph=current_start,
                    end_paragraph=index - 1,
                    heading_paragraph=current_heading,
                )
            )

        current_title = normalize_section_title(paragraph)
        current_start = index
        current_heading = index

    sections.append(
        SectionSpan(
            title=current_title,
            start_paragraph=current_start,
            end_paragraph=len(paragraphs) - 1,
            heading_paragraph=current_heading,
        )
    )
    return SectionSplitResult(document=document, sections=sections)


def is_section_heading(paragraph: str) -> bool:
    """Return whether a paragraph looks like a section/subsection heading."""

    text = paragraph.strip()
    if not text or "\n" in text:
        return False
    if _MARKDOWN_HEADING_RE.match(text):
        return True
    if _CHINESE_LIST_HEADING_RE.match(text):
        return True
    if _CHINESE_ARTICLE_HEADING_RE.match(text):
        return True
    if _NUMERIC_HEADING_RE.match(text):
        return True
    return _looks_like_short_standalone_title(text)


def normalize_section_title(paragraph: str) -> str:
    """Normalize heading text while preserving human-readable numbering."""

    text = paragraph.strip()
    markdown_match = _MARKDOWN_HEADING_RE.match(text)
    if markdown_match:
        return markdown_match.group(2).strip()
    return text


def _looks_like_short_standalone_title(text: str) -> bool:
    if len(text) > _MAX_SHORT_TITLE_LENGTH:
        return False
    if text[-1] in _TITLE_TRAILING_PUNCTUATION:
        return False
    if any(char in text for char in _SENTENCE_PUNCTUATION):
        return False
    if not any("\u4e00" <= char <= "\u9fff" or char.isdigit() or char.isalpha() for char in text):
        return False
    return bool(_SHORT_TITLE_PREFIX_RE.match(text) or _has_title_like_suffix(text) or len(text) <= 12)


def _has_title_like_suffix(text: str) -> bool:
    return text.endswith(("条件", "范围", "材料", "流程", "期限", "对象", "要求", "标准", "方式", "程序", "附则"))


__all__ = [
    "SectionSpan",
    "SectionSplitResult",
    "is_section_heading",
    "normalize_section_title",
    "split_sections",
]
