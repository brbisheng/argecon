"""Query normalization entrypoint with cleaning, synonym mapping, and tokenization."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from src.normalize.synonym_normalizer import ReplacementHit, SynonymNormalizer

_CJK_PUNCT_TRANSLATION = str.maketrans(
    {
        "，": " ",
        "。": " ",
        "、": " ",
        "；": " ",
        "：": " ",
        "（": " ",
        "）": " ",
        "【": " ",
        "】": " ",
        "？": " ",
        "！": " ",
        ",": " ",
        ".": " ",
        ";": " ",
        ":": " ",
        "(": " ",
        ")": " ",
        "[": " ",
        "]": " ",
        "?": " ",
        "!": " ",
        "\n": " ",
        "\t": " ",
    }
)

_DEFAULT_STOPWORDS = {
    "我",
    "我们",
    "想",
    "我想",
    "想问",
    "请问",
    "一下",
    "一下子",
    "还有",
    "一点",
    "现在",
    "去年",
    "今年",
    "这个",
    "那个",
    "能不能",
    "可以",
    "看看",
}


class QueryNormalizer:
    """Normalize user queries into inspectable lexical signals."""

    def __init__(
        self,
        *,
        synonym_normalizer: SynonymNormalizer | None = None,
        stopword_path: str | Path | None = None,
    ) -> None:
        self.synonym_normalizer = synonym_normalizer or SynonymNormalizer()
        self.stopword_path = Path(stopword_path) if stopword_path else _default_stopword_path()
        self.stopwords = _load_stopwords(self.stopword_path)

    def normalize_query(self, query: str, *, remove_stopwords: bool = True) -> dict[str, Any]:
        original_query = query
        text = query.strip()
        trace: list[dict[str, Any]] = []

        cleaned = _clean_text(text)
        trace.append({"step": "text_cleaning", "before": original_query, "after": cleaned})

        punct_normalized = _normalize_punctuation(cleaned)
        trace.append({"step": "punctuation_normalization", "before": cleaned, "after": punct_normalized})

        synonym_mapped, replacement_hits = self.synonym_normalizer.replace(punct_normalized)
        trace.append(
            {
                "step": "synonym_mapping",
                "before": punct_normalized,
                "after": synonym_mapped,
                "replacements": [
                    {
                        "alias": hit.alias,
                        "canonical_term": hit.canonical_term,
                        "category": hit.category,
                        "span": [hit.start, hit.end],
                    }
                    for hit in replacement_hits
                ],
            }
        )

        tokens = _lightweight_tokenize(synonym_mapped, self.synonym_normalizer, replacement_hits)
        trace.append({"step": "lightweight_tokenization", "after": tokens})

        if remove_stopwords:
            filtered_tokens = [token for token in tokens if token not in self.stopwords]
            trace.append(
                {
                    "step": "stopword_cleanup",
                    "enabled": True,
                    "before": tokens,
                    "after": filtered_tokens,
                    "removed": [token for token, count in (Counter(tokens) - Counter(filtered_tokens)).items() for _ in range(count)],
                }
            )
        else:
            filtered_tokens = tokens
            trace.append({"step": "stopword_cleanup", "enabled": False, "after": filtered_tokens})

        detected_terms = _detect_terms(filtered_tokens, replacement_hits, self.synonym_normalizer)
        normalized_query = " ".join(filtered_tokens)
        trace.append(
            {
                "step": "finalize",
                "normalized_query": normalized_query,
                "detected_terms": detected_terms,
            }
        )

        return {
            "original_query": original_query,
            "normalized_query": normalized_query,
            "detected_terms": detected_terms,
            "normalization_trace": trace,
        }



def _clean_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text



def _normalize_punctuation(text: str) -> str:
    normalized = text.translate(_CJK_PUNCT_TRANSLATION)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()



def _lightweight_tokenize(
    text: str,
    synonym_normalizer: SynonymNormalizer,
    replacement_hits: list[ReplacementHit],
) -> list[str]:
    canonical_terms = [entry.term for entry in synonym_normalizer.entries]
    ordered_terms = sorted(canonical_terms, key=len, reverse=True)
    remaining = text
    detected_tokens: list[str] = []

    for term in ordered_terms:
        if term not in remaining:
            continue
        count = remaining.count(term)
        for _ in range(count):
            detected_tokens.append(term)
        remaining = remaining.replace(term, " ")

    residual_tokens = [token.strip() for token in re.split(r"\s+", remaining) if token.strip()]
    residual_tokens = [token for token in residual_tokens if not _is_noise(token)]

    tokens = detected_tokens + residual_tokens
    if replacement_hits:
        preferred_order = []
        seen: set[str] = set()
        for hit in replacement_hits:
            if hit.canonical_term not in seen:
                preferred_order.append(hit.canonical_term)
                seen.add(hit.canonical_term)
        leftovers = [token for token in tokens if token not in seen]
        return preferred_order + leftovers
    return tokens



def _detect_terms(
    tokens: list[str],
    replacement_hits: list[ReplacementHit],
    synonym_normalizer: SynonymNormalizer,
) -> list[str]:
    canonical_lookup = {entry.term for entry in synonym_normalizer.entries}
    detected: list[str] = []
    seen: set[str] = set()

    for hit in replacement_hits:
        if hit.canonical_term not in seen:
            seen.add(hit.canonical_term)
            detected.append(hit.canonical_term)

    for token in tokens:
        if token in canonical_lookup and token not in seen:
            seen.add(token)
            detected.append(token)

    return detected



def _is_noise(token: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-zA-Z]+", token)) or len(token) == 1



def _load_stopwords(stopword_path: Path) -> set[str]:
    words = set(_DEFAULT_STOPWORDS)
    if not stopword_path.exists():
        return words
    for line in stopword_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        words.add(stripped)
    return words



def _default_stopword_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "stopwords.txt"


__all__ = ["QueryNormalizer"]
