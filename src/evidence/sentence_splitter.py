"""Chinese policy-oriented sentence splitting utilities."""

from __future__ import annotations

import re

_SENTENCE_BREAK_RE = re.compile(r"(?<=[。！？!?；;])")
_STRUCTURAL_MARKER_RE = re.compile(
    r"(?=(?:第[一二三四五六七八九十百千万0-9]+条|第[一二三四五六七八九十百千万0-9]+款|"
    r"[（(][一二三四五六七八九十0-9]+[)）]|[一二三四五六七八九十]+、|[0-9]+[、.]))"
)
_WHITESPACE_RE = re.compile(r"[\t\r\f\v ]+")


def split_sentences(text: str, *, max_sentence_length: int = 120) -> list[str]:
    """Split Chinese policy text into sentence-like units.

    The splitter prefers sentence-final punctuation such as ``。`` and ``；`` while
    also respecting common policy/article structures like ``第二条`` or ``（一）``.
    Very long spans are further broken by structural markers to keep evidence units
    readable for lexical matching.
    """

    normalized = _normalize_text(text)
    if not normalized:
        return []

    coarse_segments = _split_by_punctuation(normalized)
    sentences: list[str] = []
    for segment in coarse_segments:
        sentences.extend(_split_long_segment(segment, max_sentence_length=max_sentence_length))

    return _merge_short_segments(sentences)



def _normalize_text(text: str) -> str:
    normalized = text.replace("\u3000", " ")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]*\n+[ \t]*", "\n", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    normalized = normalized.strip()
    return normalized



def _split_by_punctuation(text: str) -> list[str]:
    pieces: list[str] = []
    for block in text.split("\n"):
        stripped = block.strip()
        if not stripped:
            continue
        parts = _SENTENCE_BREAK_RE.split(stripped)
        for part in parts:
            cleaned = part.strip(" ，、")
            if cleaned:
                pieces.append(cleaned)
    return pieces



def _split_long_segment(segment: str, *, max_sentence_length: int) -> list[str]:
    if len(segment) <= max_sentence_length:
        return [segment]

    fragments = [fragment.strip(" ，、") for fragment in _STRUCTURAL_MARKER_RE.split(segment) if fragment.strip(" ，、")]
    if len(fragments) <= 1:
        fragments = [fragment.strip(" ，、") for fragment in re.split(r"(?<=[，、：:])", segment) if fragment.strip(" ，、")]
    if len(fragments) <= 1:
        return [segment]

    merged: list[str] = []
    buffer = ""
    for fragment in fragments:
        candidate = f"{buffer}{fragment}" if buffer else fragment
        if buffer and len(candidate) > max_sentence_length:
            merged.append(buffer.strip())
            buffer = fragment
        else:
            buffer = candidate
    if buffer:
        merged.append(buffer.strip())
    return merged or [segment]



def _merge_short_segments(segments: list[str]) -> list[str]:
    merged: list[str] = []
    for segment in segments:
        cleaned = segment.strip()
        if not cleaned:
            continue
        if merged and len(cleaned) <= 8 and not _looks_like_structure(cleaned):
            merged[-1] = f"{merged[-1]}{cleaned}"
            continue
        merged.append(cleaned)
    return merged



def _looks_like_structure(text: str) -> bool:
    return bool(
        re.match(
            r"^(?:第[一二三四五六七八九十百千万0-9]+[条款]|[（(][一二三四五六七八九十0-9]+[)）]|[一二三四五六七八九十]+、|[0-9]+[、.])",
            text,
        )
    )


__all__ = ["split_sentences"]
