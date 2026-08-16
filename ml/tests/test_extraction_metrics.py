"""Unit tests for ml/graph/experiments/metrics.py's fact-level scoring."""

from ml.graph.experiments.metrics import score_medications, score_observations


def test_score_medications_perfect_match():
    ground_truth = [{"name": "lisinopril", "dosage": "20mg", "frequency": "daily", "status": "started"}]
    extracted = [{"name": "Lisinopril", "dosage": "20mg", "frequency": "daily", "status": "started"}]
    scores = score_medications(extracted, ground_truth)
    assert scores == {"name_recall": 1.0, "dosage_accuracy": 1.0, "frequency_accuracy": 1.0, "status_accuracy": 1.0}


def test_score_medications_name_matched_but_wrong_dosage():
    ground_truth = [{"name": "lisinopril", "dosage": "20mg", "frequency": "daily", "status": "started"}]
    extracted = [{"name": "lisinopril", "dosage": "10mg", "frequency": "daily", "status": "started"}]
    scores = score_medications(extracted, ground_truth)
    assert scores["name_recall"] == 1.0
    assert scores["dosage_accuracy"] == 0.0


def test_score_medications_missed_medication_scores_zero_across_fields():
    ground_truth = [{"name": "aspirin", "dosage": "81mg", "frequency": "daily", "status": "discontinued"}]
    scores = score_medications([], ground_truth)
    assert scores == {"name_recall": 0.0, "dosage_accuracy": 0.0, "frequency_accuracy": 0.0, "status_accuracy": 0.0}


def test_score_medications_empty_ground_truth_scores_perfect():
    assert score_medications([{"name": "anything"}], []) == {
        "name_recall": 1.0, "dosage_accuracy": 1.0, "frequency_accuracy": 1.0, "status_accuracy": 1.0,
    }


def test_score_observations_perfect_match():
    ground_truth = [{"name": "Cardiothoracic ratio", "value": "0.48"}]
    extracted = [{"name": "cardiothoracic ratio", "value": "0.48"}]
    assert score_observations(extracted, ground_truth) == {"name_recall": 1.0, "value_accuracy": 1.0}


def test_score_observations_wrong_value():
    ground_truth = [{"name": "Cardiothoracic ratio", "value": "0.48"}]
    extracted = [{"name": "Cardiothoracic ratio", "value": "0.58"}]
    scores = score_observations(extracted, ground_truth)
    assert scores["name_recall"] == 1.0
    assert scores["value_accuracy"] == 0.0
