"""Unit tests for ml/claims/confidence.py's score combination."""

from ml.claims.confidence import compute_confidence


def test_confidence_is_higher_for_top_ranked_authoritative_entailed_claim():
    high = compute_confidence(entailment_prob=0.95, contradiction_prob=0.0, retrieval_rank=0, authority=0.9)
    low = compute_confidence(entailment_prob=0.95, contradiction_prob=0.0, retrieval_rank=4, authority=0.3)
    assert high > low


def test_confidence_is_zero_when_contradiction_outweighs_entailment():
    confidence = compute_confidence(entailment_prob=0.1, contradiction_prob=0.9, retrieval_rank=0, authority=0.9)
    # net_entailment clamps to 0, so only retrieval + authority contribute
    assert confidence == 0.25 * 1.0 + 0.25 * 0.9


def test_confidence_stays_within_zero_one_bounds():
    assert 0.0 <= compute_confidence(1.0, 0.0, 0, 1.0) <= 1.0
    assert 0.0 <= compute_confidence(0.0, 1.0, 99, 0.0) <= 1.0
