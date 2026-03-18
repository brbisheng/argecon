"""BM25 chunk retriever that only handles lexical retrieval over chunk indexes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from src.common import RetrievedChunk
from src.retrieve.index_store import ChunkIndex, load_chunk_index, tokenize_for_retrieval


@dataclass(slots=True)
class BM25Retriever:
    """Pure-Python BM25 retriever over preloaded chunk indexes."""

    index: ChunkIndex
    k1: float = 1.5
    b: float = 0.75
    epsilon: float = 1e-9

    @classmethod
    def from_chunk_store(
        cls,
        *,
        data_dir: str | None = None,
        chunk_path: str | None = None,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> "BM25Retriever":
        return cls(index=load_chunk_index(data_dir=data_dir, chunk_path=chunk_path), k1=k1, b=b)

    def retrieve(
        self,
        normalized_query: str,
        *,
        top_k: int = 5,
        region: str | None = None,
    ) -> list[RetrievedChunk]:
        """Rank chunks for a normalized query and return top-k chunk hits."""

        query_terms = tokenize_for_retrieval(normalized_query)
        if not query_terms or not self.index.chunks or top_k <= 0:
            return []

        ranked_scores: list[tuple[int, float, list[str]]] = []
        doc_count = len(self.index.chunks)
        avg_doc_len = self.index.average_document_length or 1.0
        normalized_region = region.casefold() if region else None

        for doc_index, chunk in enumerate(self.index.chunks):
            if normalized_region and chunk.region.casefold() != normalized_region:
                continue

            doc_len = self.index.document_lengths[doc_index] or 1
            term_freqs = self.index.term_frequencies[doc_index]
            matched_terms: list[str] = []
            score = 0.0

            for term in query_terms:
                frequency = term_freqs.get(term, 0)
                if frequency == 0:
                    continue
                matched_terms.append(term)
                document_frequency = self.index.document_frequencies.get(term, 0)
                idf = math.log(1 + ((doc_count - document_frequency + 0.5) / (document_frequency + 0.5)))
                numerator = frequency * (self.k1 + 1)
                denominator = frequency + self.k1 * (1 - self.b + self.b * (doc_len / avg_doc_len))
                score += idf * (numerator / (denominator + self.epsilon))

            if score > 0:
                ranked_scores.append((doc_index, score, matched_terms))

        ranked_scores.sort(key=lambda item: item[1], reverse=True)
        return self._build_results(ranked_scores[:top_k])

    def _build_results(self, ranked_scores: Sequence[tuple[int, float, list[str]]]) -> list[RetrievedChunk]:
        results: list[RetrievedChunk] = []
        for rank, (doc_index, score, matched_terms) in enumerate(ranked_scores, start=1):
            results.append(
                RetrievedChunk(
                    chunk=self.index.chunks[doc_index],
                    retrieval_score=score,
                    retrieval_rank=rank,
                    match_terms=matched_terms,
                    retriever_name="bm25",
                )
            )
        return results


__all__ = ["BM25Retriever"]
