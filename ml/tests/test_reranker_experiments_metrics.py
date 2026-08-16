"""Unit tests for ml/rag/reranker_experiments/metrics.py's hit-rate scoring."""

from ml.rag.reranker_experiments.metrics import hit_at_1, hit_at_3, included


def test_hit_at_1_true_when_top_source_matches_patient_fact():
    assert hit_at_1(["patient_document", "medlineplus"], "patient_fact") is True


def test_hit_at_1_false_when_top_source_is_wrong_type():
    assert hit_at_1(["medlineplus", "patient_document"], "patient_fact") is False


def test_hit_at_1_accepts_either_reference_source_for_general_topic():
    assert hit_at_1(["pubmed"], "general_topic") is True
    assert hit_at_1(["medlineplus"], "general_topic") is True
    assert hit_at_1(["patient_document"], "general_topic") is False


def test_hit_at_1_false_for_empty_results():
    assert hit_at_1([], "patient_fact") is False


def test_hit_at_3_true_if_match_anywhere_in_top_three():
    assert hit_at_3(["medlineplus", "pubmed", "patient_document"], "patient_fact") is True


def test_hit_at_3_ignores_matches_beyond_top_three():
    assert hit_at_3(["medlineplus", "pubmed", "usda", "patient_document"], "patient_fact") is False


def test_included_true_for_a_match_anywhere_in_the_full_set():
    # Distinct from hit@3: a match in the last position of a 5-item set
    # still counts, since qa_chain.py's LLM reads the whole evidence set.
    assert included(["medlineplus", "pubmed", "usda", "medlineplus", "patient_document"], "patient_fact") is True


def test_included_false_when_expected_source_never_appears():
    assert included(["medlineplus", "pubmed"], "patient_fact") is False
