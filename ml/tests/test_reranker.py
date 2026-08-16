"""
Unit tests for ml/rag/reranker.py's scoring/combination logic.

Uses a stub subclass that skips loading the real cross-encoder (no
network/GPU dependency) and injects fixed relevance scores, so these tests
exercise the authority/recency/weighting logic in isolation.
"""

from datetime import date, timedelta

from ml.rag.reranker import RECENCY_HALF_LIFE_DAYS, Reranker
from ml.rag.retriever import Chunk


class StubReranker(Reranker):
    """Reranker with a fixed relevance score per chunk, no model loaded."""

    def __init__(self, relevance_scores: list[float]) -> None:
        self._relevance_scores_fixture = relevance_scores

    def _relevance_scores(self, query: str, chunks: list[Chunk]) -> list[float]:
        return self._relevance_scores_fixture


def test_authority_score_defaults_to_neutral_when_missing_or_invalid():
    assert Reranker._authority_score(Chunk(id="a", text="x", metadata={})) == 0.5
    assert Reranker._authority_score(Chunk(id="a", text="x", metadata={"authority": "high"})) == 0.5
    assert Reranker._authority_score(Chunk(id="a", text="x", metadata={"authority": 1.5})) == 0.5


def test_authority_score_uses_metadata_value_when_valid():
    chunk = Chunk(id="a", text="x", metadata={"authority": 0.9})
    assert Reranker._authority_score(chunk) == 0.9


def test_recency_score_defaults_to_neutral_when_missing_or_unparseable():
    assert Reranker._recency_score(Chunk(id="a", text="x", metadata={})) == 0.5
    assert Reranker._recency_score(Chunk(id="a", text="x", metadata={"published_date": "not-a-date"})) == 0.5


def test_recency_score_decays_by_half_at_one_half_life():
    stale_date = (date.today() - timedelta(days=RECENCY_HALF_LIFE_DAYS)).isoformat()
    chunk = Chunk(id="a", text="x", metadata={"published_date": stale_date})
    assert abs(Reranker._recency_score(chunk) - 0.5) < 0.01


def test_recency_score_decays_further_at_two_half_lives():
    stale_date = (date.today() - timedelta(days=2 * RECENCY_HALF_LIFE_DAYS)).isoformat()
    chunk = Chunk(id="a", text="x", metadata={"published_date": stale_date})
    assert abs(Reranker._recency_score(chunk) - 0.25) < 0.01


def test_rerank_lets_authority_and_recency_break_relevance_ties():
    chunks = [
        Chunk(id="low_authority", text="x", metadata={"authority": 0.1}),
        Chunk(id="high_authority", text="x", metadata={"authority": 0.9}),
    ]
    reranker = StubReranker(relevance_scores=[0.5, 0.5])

    ranked = reranker.rerank("query", chunks)

    assert [c.id for c in ranked] == ["high_authority", "low_authority"]


def test_rerank_respects_top_k():
    chunks = [Chunk(id=str(i), text="x", metadata={}) for i in range(5)]
    reranker = StubReranker(relevance_scores=[0.1, 0.9, 0.3, 0.7, 0.5])

    ranked = reranker.rerank("query", chunks, top_k=2)

    assert [c.id for c in ranked] == ["1", "3"]


def test_rerank_returns_empty_for_no_chunks():
    reranker = StubReranker(relevance_scores=[])
    assert reranker.rerank("query", []) == []
