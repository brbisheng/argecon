"""Simple TF-IDF baseline retriever for retrieval comparisons and fallback usage."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from src.common import RetrievedChunk
from src.retrieve.index_store import ChunkIndex, load_chunk_index, tokenize_for_retrieval


@dataclass(slots=True)
class TfidfRetriever:
    """Pure-Python TF-IDF cosine-style retriever used as a baseline/fallback."""

    index: ChunkIndex

    @classmethod
    def from_chunk_store(
        cls,
        *,
        data_dir: str | None = None,
        chunk_path: str | None = None,
    ) -> "TfidfRetriever":
        return cls(index=load_chunk_index(data_dir=data_dir, chunk_path=chunk_path))

    def retrieve(
        self,
        normalized_query: str,
        *,
        top_k: int = 5,
        region: str | None = None,
    ) -> list[RetrievedChunk]:
        query_terms = tokenize_for_retrieval(normalized_query)
        if not query_terms or not self.index.chunks or top_k <= 0:
            return []

        query_counts = Counter(query_terms)
        query_vector = {term: self._tfidf(term, count, len(query_terms)) for term, count in query_counts.items()}
        query_norm = math.sqrt(sum(weight * weight for weight in query_vector.values())) or 1.0
        normalized_region = region.casefold() if region else None

        scored_results: list[tuple[int, float, list[str]]] = []
        for doc_index, chunk in enumerate(self.index.chunks):
            if normalized_region and chunk.region.casefold() != normalized_region:
                continue

            term_counts = self.index.term_frequencies[doc_index]
            doc_length = self.index.document_lengths[doc_index] or 1
            shared_terms = [term for term in query_vector if term_counts.get(term, 0) > 0]
            if not shared_terms:
                continue

            doc_vector = {term: self._tfidf(term, term_counts[term], doc_length) for term in shared_terms}
            dot_product = sum(query_vector[term] * doc_vector[term] for term in shared_terms)
            doc_norm = math.sqrt(sum(weight * weight for weight in doc_vector.values())) or 1.0
            score = dot_product / (query_norm * doc_norm)
            if score > 0:
                scored_results.append((doc_index, score, shared_terms))

        scored_results.sort(key=lambda item: item[1], reverse=True)
        return [
            RetrievedChunk(
                chunk=self.index.chunks[doc_index],
                retrieval_score=score,
                retrieval_rank=rank,
                match_terms=matched_terms,
                retriever_name="tfidf",
            )
            for rank, (doc_index, score, matched_terms) in enumerate(scored_results[:top_k], start=1)
        ]

    def _tfidf(self, term: str, frequency: int, length: int) -> float:
        tf = frequency / max(length, 1)
        doc_count = len(self.index.chunks)
        document_frequency = self.index.document_frequencies.get(term, 0)
        idf = math.log(1 + (doc_count + 1) / (document_frequency + 1)) + 1
        return tf * idf


__all__ = ["TfidfRetriever"]
