"""
Live integration test for ml/graph/prose_extraction.py against the real
qwen3.5:9b model (the winning candidate from
ml/graph/experiments/RESULTS.md) — no mocking, since the actual thing
worth verifying is that a real model call plus schema-constrained
decoding produces correctly-shaped output, not just that our own parsing
code runs.
"""

from ml.graph.prose_extraction import extract_facts


def test_extract_facts_from_real_clinical_text():
    text = (
        "Patient is a 54-year-old presenting for follow-up of hypertension. "
        "Plan: increase lisinopril to 20mg daily. Blood pressure measured at 148/92 mmHg."
    )

    facts = extract_facts(text)

    assert {"medications", "conditions", "observations"} <= facts.keys()
    med_names = {m["name"].lower() for m in facts["medications"]}
    assert "lisinopril" in med_names
    condition_names = {c["name"].lower() for c in facts["conditions"]}
    assert "hypertension" in condition_names


def test_extract_facts_returns_empty_lists_for_text_with_no_facts():
    facts = extract_facts("The weather today is sunny with a light breeze.")
    assert facts == {"medications": [], "conditions": [], "observations": []}
