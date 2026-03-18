from __future__ import annotations

from src.normalize.query_normalizer import QueryNormalizer
from src.normalize.synonym_normalizer import SynonymNormalizer


def test_synonym_normalizer_replaces_high_frequency_domain_aliases() -> None:
    normalizer = SynonymNormalizer()

    normalized, hits = normalizer.replace("想借点钱买化肥，去年还有一点没还完")

    assert normalized == "想贷款农业生产资料投入，去年未结清贷款"
    assert [hit.canonical_term for hit in hits] == ["贷款", "农业生产资料投入", "未结清贷款"]
    assert hits[0].alias == "借点钱"
    assert hits[1].alias == "买化肥"
    assert hits[2].canonical_term == "未结清贷款"


def test_query_normalizer_returns_inspectable_trace_and_detected_terms() -> None:
    normalizer = QueryNormalizer()

    result = normalizer.normalize_query("我想借点钱买化肥，去年还有一点没还完")

    assert result["original_query"] == "我想借点钱买化肥，去年还有一点没还完"
    assert result["normalized_query"] == "贷款 农业生产资料投入 未结清贷款"
    assert result["detected_terms"] == ["贷款", "农业生产资料投入", "未结清贷款"]
    assert [step["step"] for step in result["normalization_trace"]] == [
        "text_cleaning",
        "punctuation_normalization",
        "synonym_mapping",
        "lightweight_tokenization",
        "stopword_cleanup",
        "finalize",
    ]


def test_query_normalizer_keeps_residual_terms_when_stopword_cleanup_disabled() -> None:
    normalizer = QueryNormalizer()

    result = normalizer.normalize_query("现在想续一下去年的贷款", remove_stopwords=False)

    assert result["detected_terms"] == ["续贷", "贷款"]
    assert "现在" in result["normalized_query"]
    assert "去年的" in result["normalized_query"] or "去年" in result["normalized_query"]
    assert result["normalization_trace"][-2]["enabled"] is False
