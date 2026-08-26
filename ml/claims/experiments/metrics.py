"""
Scoring for the NLI model-selection benchmark: accuracy plus per-class
precision/recall/F1, since a claim-verification model that's accurate
overall but weak specifically at catching contradictions would be
dangerous for PHIRE's "never surface an unsupported/conflicting claim as
fact" requirement.
"""

_LABELS = ("entailment", "neutral", "contradiction")


def accuracy(predictions: list[str], gold: list[str]) -> float:
    """Fraction of predictions matching gold labels exactly."""
    return sum(p == g for p, g in zip(predictions, gold)) / len(gold)


def per_class_f1(predictions: list[str], gold: list[str]) -> dict[str, dict[str, float]]:
    """Precision/recall/F1 for each of the three NLI labels."""
    scores = {}
    for label in _LABELS:
        true_positive = sum(p == label and g == label for p, g in zip(predictions, gold))
        predicted_positive = sum(p == label for p in predictions)
        actual_positive = sum(g == label for g in gold)

        precision = true_positive / predicted_positive if predicted_positive else 0.0
        recall = true_positive / actual_positive if actual_positive else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        scores[label] = {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}
    return scores
