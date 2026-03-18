"""Sentence-level evidence selection over retrieved chunks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.common import RetrievedChunk, SelectedEvidence
from src.evidence.sentence_splitter import split_sentences
from src.retrieve.index_store import tokenize_for_retrieval

_GENERIC_SENTENCE_HINTS = (
    "为贯彻",
    "根据",
    "依据",
    "现将",
    "如下",
    "通知如下",
    "有关事项",
    "工作要求",
)


@dataclass(slots=True)
class RankedSentence:
    """Intermediate sentence ranking record for evidence selection."""

    sentence: str
    chunk: RetrievedChunk
    score: float
    coverage: float
    overlap: int
    jaccard: float
    matched_terms: list[str]
    lexical_density: float
    generic_penalty: float



def select_evidence_sentences(
    query: str,
    retrieved_chunks: Iterable[RetrievedChunk],
    *,
    top_k_chunks: int = 3,
    max_sentences: int = 2,
) -> list[SelectedEvidence]:
    """Select top evidence sentences from retrieved chunks using lexical heuristics."""

    if max_sentences <= 0:
        return []

    query_terms = tokenize_for_retrieval(query)
    if not query_terms:
        return []

    ranked = rank_candidate_sentences(query, retrieved_chunks, top_k_chunks=top_k_chunks)
    selected: list[SelectedEvidence] = []
    seen_sentences: set[tuple[str, str]] = set()

    for index, candidate in enumerate(ranked[: max_sentences * 3], start=1):
        dedupe_key = (candidate.chunk.chunk.chunk_id, candidate.sentence)
        if dedupe_key in seen_sentences:
            continue
        seen_sentences.add(dedupe_key)
        selected.append(
            SelectedEvidence(
                evidence_id=f"{candidate.chunk.chunk.chunk_id}:sent-{index}",
                chunk_id=candidate.chunk.chunk.chunk_id,
                doc_id=candidate.chunk.chunk.doc_id,
                evidence_text=candidate.sentence,
                rationale=(
                    f"匹配词 {', '.join(candidate.matched_terms[:5])}；"
                    f"覆盖率 {candidate.coverage:.2f}；Jaccard {candidate.jaccard:.2f}"
                ),
                confidence=max(0.0, min(candidate.score, 1.0)),
                citation_text=_build_citation_text(candidate.chunk),
                metadata={
                    "score": round(candidate.score, 4),
                    "coverage": round(candidate.coverage, 4),
                    "overlap": candidate.overlap,
                    "jaccard": round(candidate.jaccard, 4),
                    "lexical_density": round(candidate.lexical_density, 4),
                    "generic_penalty": round(candidate.generic_penalty, 4),
                    "matched_terms": candidate.matched_terms,
                    "retrieval_rank": candidate.chunk.retrieval_rank,
                    "retrieval_score": candidate.chunk.retrieval_score,
                    "source_title": candidate.chunk.chunk.source_title,
                    "section_title": candidate.chunk.chunk.section_title,
                },
            )
        )
        if len(selected) >= max_sentences:
            break

    return selected



def rank_candidate_sentences(
    query: str,
    retrieved_chunks: Iterable[RetrievedChunk],
    *,
    top_k_chunks: int = 3,
) -> list[RankedSentence]:
    """Rank candidate sentences from top-k retrieved chunks."""

    query_terms = tokenize_for_retrieval(query)
    if not query_terms:
        return []

    query_term_set = set(query_terms)
    ranked_candidates: list[RankedSentence] = []
    for chunk in list(retrieved_chunks)[:top_k_chunks]:
        for sentence in split_sentences(chunk.chunk.chunk_text):
            score_record = _score_sentence(sentence, chunk, query_terms, query_term_set)
            if score_record.overlap == 0:
                continue
            ranked_candidates.append(score_record)

    ranked_candidates.sort(
        key=lambda item: (
            item.score,
            item.coverage,
            item.overlap,
            item.chunk.retrieval_score,
            -len(item.sentence),
        ),
        reverse=True,
    )
    return ranked_candidates



def _score_sentence(
    sentence: str,
    chunk: RetrievedChunk,
    query_terms: list[str],
    query_term_set: set[str],
) -> RankedSentence:
    sentence_terms = tokenize_for_retrieval(sentence)
    sentence_term_set = set(sentence_terms)
    matched_terms = [term for term in query_terms if term in sentence_term_set]
    overlap = len(set(matched_terms))
    coverage = overlap / max(len(query_term_set), 1)
    union_size = len(query_term_set | sentence_term_set) or 1
    jaccard = overlap / union_size
    lexical_density = overlap / max(len(sentence_terms), 1)
    generic_penalty = 0.12 if _is_generic_sentence(sentence, matched_terms) else 0.0
    chunk_bonus = min(chunk.retrieval_score, 1.0) * 0.15

    raw_score = coverage * 0.45 + lexical_density * 0.25 + jaccard * 0.20 + chunk_bonus + min(overlap, 4) * 0.03
    score = max(0.0, min(1.0, raw_score - generic_penalty))

    return RankedSentence(
        sentence=sentence,
        chunk=chunk,
        score=score,
        coverage=coverage,
        overlap=overlap,
        jaccard=jaccard,
        matched_terms=list(dict.fromkeys(matched_terms)),
        lexical_density=lexical_density,
        generic_penalty=generic_penalty,
    )



def _is_generic_sentence(sentence: str, matched_terms: list[str]) -> bool:
    if len(sentence) <= 18 and matched_terms:
        return False
    return any(hint in sentence for hint in _GENERIC_SENTENCE_HINTS) and len(set(matched_terms)) <= 2



def _build_citation_text(chunk: RetrievedChunk) -> str:
    section = f" - {chunk.chunk.section_title}" if chunk.chunk.section_title else ""
    return f"{chunk.chunk.source_title}{section}".strip()


__all__ = ["RankedSentence", "rank_candidate_sentences", "select_evidence_sentences"]
