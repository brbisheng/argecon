"""Synonym loading and replacement utilities for query normalization."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SynonymEntry:
    """A canonical domain term and its aliases."""

    term: str
    aliases: tuple[str, ...]
    category: str | None = None


@dataclass(frozen=True, slots=True)
class ReplacementHit:
    """A single alias replacement recorded during normalization."""

    alias: str
    canonical_term: str
    start: int
    end: int
    category: str | None = None


class SynonymNormalizer:
    """Load a synonym table and replace aliases with canonical domain terms."""

    def __init__(self, synonym_path: str | Path | None = None) -> None:
        self.synonym_path = Path(synonym_path) if synonym_path else _default_synonym_path()
        self.entries = self._load_entries(self.synonym_path)

    @cached_property
    def _alias_lookup(self) -> dict[str, SynonymEntry]:
        lookup: dict[str, SynonymEntry] = {}
        for entry in self.entries:
            for alias in sorted(set(entry.aliases), key=len, reverse=True):
                lookup[alias] = entry
        return lookup

    @cached_property
    def _combined_pattern(self) -> re.Pattern[str]:
        aliases = sorted(self._alias_lookup, key=len, reverse=True)
        return re.compile("|".join(re.escape(alias) for alias in aliases))

    def replace(self, text: str) -> tuple[str, list[ReplacementHit]]:
        """Replace configured aliases with canonical terms and return trace hits."""

        hits: list[ReplacementHit] = []

        def _replacement(match: re.Match[str]) -> str:
            alias = match.group(0)
            entry = self._alias_lookup[alias]
            replacement = entry.term
            hits.append(
                ReplacementHit(
                    alias=alias,
                    canonical_term=entry.term,
                    start=match.start(),
                    end=match.start() + len(replacement),
                    category=entry.category,
                )
            )
            return replacement

        normalized = self._combined_pattern.sub(_replacement, text)
        return normalized, hits

    @staticmethod
    def _load_entries(synonym_path: Path) -> tuple[SynonymEntry, ...]:
        payload = json.loads(synonym_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "canonical_terms" in payload:
            return tuple(_entries_from_structured_payload(payload["canonical_terms"]))
        if isinstance(payload, dict):
            return tuple(_entries_from_legacy_payload(payload))
        raise ValueError(f"Unsupported synonym payload in {synonym_path}")



def _entries_from_structured_payload(records: list[dict[str, object]]) -> list[SynonymEntry]:
    entries: list[SynonymEntry] = []
    for record in records:
        term = str(record["term"]).strip()
        aliases = tuple(str(alias).strip() for alias in record.get("aliases", []) if str(alias).strip())
        category = str(record["category"]).strip() if record.get("category") else None
        if term:
            entries.append(SynonymEntry(term=term, aliases=aliases, category=category))
    return entries



def _entries_from_legacy_payload(payload: dict[str, object]) -> list[SynonymEntry]:
    entries: list[SynonymEntry] = []
    for term, aliases in payload.items():
        if not isinstance(aliases, list):
            continue
        cleaned_aliases = tuple(str(alias).strip() for alias in aliases if str(alias).strip())
        entries.append(SynonymEntry(term=str(term).strip(), aliases=cleaned_aliases))
    return entries



def _default_synonym_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "synonyms.json"


__all__ = ["ReplacementHit", "SynonymEntry", "SynonymNormalizer"]
