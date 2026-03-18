"""Unified chunking pipeline for normalized source documents."""

from __future__ import annotations

from src.common.schemas import ChunkRecord, SourceDocument
from src.chunking.paragraph_chunker import ChunkingConfig, chunk_document as chunk_by_paragraphs
from src.chunking.section_splitter import SectionSplitResult, split_sections


def build_default_chunking_config(*, chunk_size: int = 800, chunk_overlap: int = 100) -> ChunkingConfig:
    """Map the historical ingestion chunk parameters onto paragraph-first chunking config."""

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    target = max(120, min(chunk_size, max(160, chunk_size - max(40, chunk_overlap))))
    minimum = max(80, min(target, target // 3))
    return ChunkingConfig(min_chunk_chars=minimum, target_chunk_chars=target, max_chunk_chars=chunk_size)


def chunk_document(document: SourceDocument, config: ChunkingConfig | None = None) -> list[ChunkRecord]:
    """Chunk any normalized SourceDocument via shared section + paragraph logic."""

    active_config = config or build_default_chunking_config()
    return chunk_by_paragraphs(document, active_config)


def inspect_sections(document: SourceDocument) -> SectionSplitResult:
    """Expose section detection for debugging/tests without duplicating logic."""

    return split_sections(document)


__all__ = ["ChunkingConfig", "build_default_chunking_config", "chunk_document", "inspect_sections"]
