"""Paragraph-first chunking for normalized source documents."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from src.common.schemas import ChunkRecord, SourceDocument
from src.chunking.section_splitter import SectionSpan, split_sections

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])")


@dataclass(slots=True)
class ChunkingConfig:
    """Character-based chunking controls."""

    min_chunk_chars: int = 120
    target_chunk_chars: int = 360
    max_chunk_chars: int = 800

    def __post_init__(self) -> None:
        if self.min_chunk_chars <= 0:
            raise ValueError("min_chunk_chars must be positive")
        if self.target_chunk_chars < self.min_chunk_chars:
            raise ValueError("target_chunk_chars must be >= min_chunk_chars")
        if self.max_chunk_chars < self.target_chunk_chars:
            raise ValueError("max_chunk_chars must be >= target_chunk_chars")


@dataclass(slots=True)
class _ChunkSeed:
    text: str
    paragraph_range: tuple[int, int]
    section_title: str | None


@dataclass(slots=True)
class _SectionContext:
    title: str | None
    paragraphs: list[tuple[int, str]]


def chunk_document(document: SourceDocument, config: ChunkingConfig) -> list[ChunkRecord]:
    """Chunk a normalized document with paragraph-first heuristics."""

    paragraphs = _normalized_paragraphs(document)
    if not paragraphs:
        return []

    sections = split_sections(
        SourceDocument(
            doc_id=document.doc_id,
            region=document.region,
            source_path=document.source_path,
            file_name=document.file_name,
            file_type=document.file_type,
            title=document.title,
            raw_text=document.raw_text,
            paragraphs=[text for _, text in paragraphs],
            parse_status=document.parse_status,
            parse_error=document.parse_error,
            source_format_confidence=document.source_format_confidence,
            text_quality_flag=document.text_quality_flag,
            needs_manual_review=document.needs_manual_review,
            ocr_needed=document.ocr_needed,
            ingestion_time=document.ingestion_time,
        )
    ).sections
    seeds: list[_ChunkSeed] = []

    for section in sections or [SectionSpan(title=None, start_paragraph=0, end_paragraph=len(paragraphs) - 1, heading_paragraph=None)]:
        section_paragraphs = paragraphs[section.start_paragraph : section.end_paragraph + 1]
        if not section_paragraphs:
            continue
        content = _content_paragraphs_for_section(section, section_paragraphs)
        if not content:
            content = section_paragraphs
        seeds.extend(_chunk_section(_SectionContext(title=section.title, paragraphs=content), config))

    return [_build_chunk_record(document, seed, index) for index, seed in enumerate(seeds)]


def _normalized_paragraphs(document: SourceDocument) -> list[tuple[int, str]]:
    source = document.paragraphs or [part.strip() for part in document.raw_text.split("\n\n") if part.strip()]
    normalized: list[tuple[int, str]] = []
    for index, paragraph in enumerate(source):
        text = paragraph.strip()
        if text:
            normalized.append((index, text))
    return normalized


def _content_paragraphs_for_section(section: SectionSpan, section_paragraphs: list[tuple[int, str]]) -> list[tuple[int, str]]:
    if section.heading_paragraph is None:
        return section_paragraphs
    if len(section_paragraphs) == 1:
        return section_paragraphs
    first_index, first_text = section_paragraphs[0]
    if first_index == section.heading_paragraph and first_text == (section.title or first_text):
        return section_paragraphs[1:]
    return section_paragraphs


def _chunk_section(section: _SectionContext, config: ChunkingConfig) -> list[_ChunkSeed]:
    seeds: list[_ChunkSeed] = []
    buffer_texts: list[str] = []
    buffer_start: int | None = None
    buffer_end: int | None = None

    def flush() -> None:
        nonlocal buffer_texts, buffer_start, buffer_end
        if not buffer_texts or buffer_start is None or buffer_end is None:
            buffer_texts = []
            buffer_start = None
            buffer_end = None
            return
        seeds.append(
            _ChunkSeed(
                text="\n\n".join(buffer_texts).strip(),
                paragraph_range=(buffer_start, buffer_end),
                section_title=section.title,
            )
        )
        buffer_texts = []
        buffer_start = None
        buffer_end = None

    for paragraph_index, paragraph_text in section.paragraphs:
        if len(paragraph_text) > config.max_chunk_chars:
            flush()
            seeds.extend(_split_long_paragraph(paragraph_text, paragraph_index, section.title, config))
            continue

        candidate_parts = [*buffer_texts, paragraph_text]
        candidate_text = "\n\n".join(candidate_parts)
        if buffer_texts and len(candidate_text) > config.max_chunk_chars:
            flush()
            candidate_parts = [paragraph_text]
            candidate_text = paragraph_text

        if buffer_start is None:
            buffer_start = paragraph_index
        buffer_end = paragraph_index
        buffer_texts = candidate_parts

        if len(candidate_text) >= config.target_chunk_chars:
            flush()

    flush()
    return _merge_short_seeds(seeds, config)


def _split_long_paragraph(
    paragraph_text: str,
    paragraph_index: int,
    section_title: str | None,
    config: ChunkingConfig,
) -> list[_ChunkSeed]:
    sentences = [segment.strip() for segment in _SENTENCE_SPLIT_RE.split(paragraph_text) if segment.strip()]
    if len(sentences) <= 1:
        return [
            _ChunkSeed(
                text=paragraph_text,
                paragraph_range=(paragraph_index, paragraph_index),
                section_title=section_title,
            )
        ]

    seeds: list[_ChunkSeed] = []
    buffer: list[str] = []
    for sentence in sentences:
        candidate = "".join(buffer + [sentence])
        if buffer and len(candidate) > config.max_chunk_chars:
            seeds.append(
                _ChunkSeed(
                    text="".join(buffer).strip(),
                    paragraph_range=(paragraph_index, paragraph_index),
                    section_title=section_title,
                )
            )
            buffer = [sentence]
        else:
            buffer.append(sentence)
    if buffer:
        seeds.append(
            _ChunkSeed(
                text="".join(buffer).strip(),
                paragraph_range=(paragraph_index, paragraph_index),
                section_title=section_title,
            )
        )
    return _merge_short_seeds(seeds, config)


def _merge_short_seeds(seeds: list[_ChunkSeed], config: ChunkingConfig) -> list[_ChunkSeed]:
    if not seeds:
        return []

    merged: list[_ChunkSeed] = []
    pending: _ChunkSeed | None = None

    for seed in seeds:
        if pending is None:
            pending = seed
            continue

        should_merge = (
            len(pending.text) < config.min_chunk_chars
            and pending.section_title == seed.section_title
            and len(pending.text) + 2 + len(seed.text) <= config.max_chunk_chars
        )
        if should_merge:
            pending = _ChunkSeed(
                text=f"{pending.text}\n\n{seed.text}".strip(),
                paragraph_range=(pending.paragraph_range[0], seed.paragraph_range[1]),
                section_title=pending.section_title,
            )
            continue

        merged.append(pending)
        pending = seed

    if pending is not None:
        if merged and len(pending.text) < config.min_chunk_chars:
            previous = merged[-1]
            if previous.section_title == pending.section_title and len(previous.text) + 2 + len(pending.text) <= config.max_chunk_chars:
                merged[-1] = _ChunkSeed(
                    text=f"{previous.text}\n\n{pending.text}".strip(),
                    paragraph_range=(previous.paragraph_range[0], pending.paragraph_range[1]),
                    section_title=previous.section_title,
                )
            else:
                merged.append(pending)
        else:
            merged.append(pending)

    return merged


def _build_chunk_record(document: SourceDocument, seed: _ChunkSeed, chunk_index: int) -> ChunkRecord:
    digest = hashlib.sha1(seed.text.encode("utf-8")).hexdigest()[:10]
    return ChunkRecord(
        chunk_id=f"{document.doc_id}:chunk:{chunk_index}:{digest}",
        doc_id=document.doc_id,
        region=document.region,
        source_title=document.title or document.file_name,
        chunk_text=seed.text,
        chunk_index=chunk_index,
        section_title=seed.section_title,
        paragraph_range=seed.paragraph_range,
        metadata={
            "source_path": document.source_path,
            "file_name": document.file_name,
            "parse_status": document.parse_status.value,
            "doc_id": document.doc_id,
        },
    )


__all__ = ["ChunkingConfig", "chunk_document"]
