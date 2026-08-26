"""
Scoring for the prose-extraction benchmark: fact-level matching, not text
similarity — a medication's name, dosage, frequency, and status are four
separate things that can each be right or wrong independently, and name
recall alone (the easy part) hides whether the harder fields were
actually captured.
"""

import re


def _normalize(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _find_match(name: str, candidates: list[dict]) -> dict | None:
    """Find the candidate whose name substring-matches name (case-insensitive, either direction)."""
    target = _normalize(name)
    for candidate in candidates:
        candidate_name = _normalize(candidate.get("name"))
        if candidate_name and (target in candidate_name or candidate_name in target):
            return candidate
    return None


def score_medications(extracted: list[dict], ground_truth: list[dict]) -> dict[str, float]:
    """Per-field accuracy against ground truth: name recall, then dosage/frequency/status among name-matches."""
    if not ground_truth:
        return {"name_recall": 1.0, "dosage_accuracy": 1.0, "frequency_accuracy": 1.0, "status_accuracy": 1.0}

    name_hits = dosage_hits = frequency_hits = status_hits = 0
    for gt in ground_truth:
        match = _find_match(gt["name"], extracted)
        if not match:
            continue
        name_hits += 1
        if _normalize(gt.get("dosage")) == _normalize(match.get("dosage")):
            dosage_hits += 1
        gt_freq, match_freq = _normalize(gt.get("frequency")), _normalize(match.get("frequency"))
        if gt_freq and (gt_freq in match_freq or match_freq in gt_freq):
            frequency_hits += 1
        if _normalize(gt.get("status")) == _normalize(match.get("status")):
            status_hits += 1

    n = len(ground_truth)
    return {
        "name_recall": name_hits / n,
        "dosage_accuracy": dosage_hits / n,
        "frequency_accuracy": frequency_hits / n,
        "status_accuracy": status_hits / n,
    }


def score_observations(extracted: list[dict], ground_truth: list[dict]) -> dict[str, float]:
    """Per-field accuracy for observations: name recall, then value accuracy among name-matches."""
    if not ground_truth:
        return {"name_recall": 1.0, "value_accuracy": 1.0}

    name_hits = value_hits = 0
    for gt in ground_truth:
        match = _find_match(gt["name"], extracted)
        if not match:
            continue
        name_hits += 1
        if _normalize(gt.get("value")) == _normalize(match.get("value")):
            value_hits += 1

    n = len(ground_truth)
    return {"name_recall": name_hits / n, "value_accuracy": value_hits / n}
