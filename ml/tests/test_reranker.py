"""
Unit tests for ml/rag/reranker.py's scoring/combination logic.

Uses a stub subclass that skips loading the real cross-encoder (no
network/GPU dependency) and injects fixed relevance scores, so these tests
exercise the authority/recency/weighting logic in isolation.
"""

from datetime import date, timedelta

from ml.rag.reranker import AUTHORITY_WEIGHT, RECENCY_HALF_LIFE_DAYS, RECENCY_WEIGHT, RELEVANCE_WEIGHT, Reranker
from ml.rag.retriever import Chunk


class StubReranker(Reranker):
    """Reranker with a fixed relevance score per chunk, no model loaded."""

    def __init__(self, relevance_scores: list[float], enable_patient_floor: bool = True) -> None:
        self._relevance_scores_fixture = relevance_scores
        self.relevance_weight = RELEVANCE_WEIGHT
        self.authority_weight = AUTHORITY_WEIGHT
        self.recency_weight = RECENCY_WEIGHT
        self.enable_patient_floor = enable_patient_floor

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


def test_custom_weights_change_ranking():
    # Two chunks tied on relevance; only authority differs. Default
    # weights should already favor the higher-authority chunk (already
    # covered by test_rerank_lets_authority_and_recency_break_relevance_ties);
    # this confirms the weights are actually instance-configurable, not
    # just module constants baked into _combine.
    chunks = [
        Chunk(id="low_authority", text="x", metadata={"authority": 0.1}),
        Chunk(id="high_authority", text="x", metadata={"authority": 0.9}),
    ]
    reranker = StubReranker(relevance_scores=[0.5, 0.5])
    reranker.relevance_weight, reranker.authority_weight, reranker.recency_weight = 1.0, 0.0, 0.0

    # With authority_weight=0, the two chunks' combined scores collapse
    # to equal -- proves the weights are live instance state _combine
    # actually reads, not module constants baked in at import time.
    scores = {c.id: reranker._combine(0.5, c) for c in chunks}
    assert scores["low_authority"] == scores["high_authority"] == 0.5


def test_patient_floor_promotes_close_relevance_patient_chunk_into_top_k():
    # Mirrors the real failure this fixes: several reference chunks tied
    # at max relevance, the patient's own chunk close behind (within
    # PATIENT_FLOOR_RELEVANCE_MARGIN) but not close enough to make top_k
    # on weighted score alone.
    chunks = [
        Chunk(id="ref1", text="x", metadata={"authority": 0.9}),
        Chunk(id="ref2", text="x", metadata={"authority": 0.9}),
        Chunk(id="ref3", text="x", metadata={"authority": 0.9}),
        Chunk(id="patient", text="x", metadata={"authority": 1.0, "source": "patient_document"}),
    ]
    reranker = StubReranker(relevance_scores=[1.0, 1.0, 1.0, 0.93])

    ranked = reranker.rerank("query", chunks, top_k=3)

    assert "patient" in [c.id for c in ranked]
    assert len(ranked) == 3


def test_patient_floor_does_not_force_in_an_unrelated_patient_chunk():
    # The patient chunk's relevance is far below the pool's best -- a
    # genuinely unrelated match should not be forced into the result just
    # because it's a patient document.
    chunks = [
        Chunk(id="ref1", text="x", metadata={"authority": 0.9}),
        Chunk(id="ref2", text="x", metadata={"authority": 0.9}),
        Chunk(id="patient", text="x", metadata={"authority": 1.0, "source": "patient_document"}),
    ]
    reranker = StubReranker(relevance_scores=[1.0, 1.0, 0.3])

    ranked = reranker.rerank("query", chunks, top_k=2)

    assert "patient" not in [c.id for c in ranked]


def test_patient_floor_margin_uses_best_relevance_not_top_combined_score():
    # ranked[0] (best *combined* score) is deliberately NOT the chunk
    # with the best *relevance* here: "top_combined" wins on combined
    # score via authority+recency despite lower relevance than
    # "high_relevance". A margin check against ranked[0]'s relevance
    # (0.7) would wrongly consider the patient chunk (relevance 0.75)
    # "close enough" (gap -0.05) and promote it -- the correct gap
    # against the pool's true best relevance (1.0) is 0.25, outside
    # PATIENT_FLOOR_RELEVANCE_MARGIN, so it should NOT be promoted.
    today = date.today().isoformat()
    chunks = [
        Chunk(id="high_relevance", text="x", metadata={}),
        Chunk(id="top_combined", text="x", metadata={"authority": 1.0, "published_date": today}),
        Chunk(id="patient", text="x", metadata={"source": "patient_document"}),
    ]
    reranker = StubReranker(relevance_scores=[1.0, 0.7, 0.75])

    ranked = reranker.rerank("query", chunks, top_k=2)

    assert [c.id for c in ranked] == ["top_combined", "high_relevance"]
    assert "patient" not in [c.id for c in ranked]


def test_patient_floor_disabled_leaves_ranking_untouched():
    chunks = [
        Chunk(id="ref1", text="x", metadata={"authority": 0.9}),
        Chunk(id="ref2", text="x", metadata={"authority": 0.9}),
        Chunk(id="ref3", text="x", metadata={"authority": 0.9}),
        Chunk(id="patient", text="x", metadata={"authority": 1.0, "source": "patient_document"}),
    ]
    reranker = StubReranker(relevance_scores=[1.0, 1.0, 1.0, 0.93], enable_patient_floor=False)

    ranked = reranker.rerank("query", chunks, top_k=3)

    assert "patient" not in [c.id for c in ranked]


def test_patient_floor_no_op_when_patient_chunk_already_in_top_k():
    chunks = [
        Chunk(id="patient", text="x", metadata={"authority": 1.0, "source": "patient_document"}),
        Chunk(id="ref1", text="x", metadata={"authority": 0.9}),
    ]
    reranker = StubReranker(relevance_scores=[1.0, 0.5])

    ranked = reranker.rerank("query", chunks, top_k=2)

    assert [c.id for c in ranked] == ["patient", "ref1"]
