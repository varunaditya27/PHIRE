"""
Tests for ml/graph/prose_extraction.py: a live integration test against
the real qwen3.5:9b model (the winning candidate from
ml/graph/experiments/RESULTS.md) for the happy path, plus mocked-failure
tests for the error-handling contract (no network needed there — the
point is verifying extract_facts() degrades to empty facts on any
failure, not retesting the model itself).
"""

import json

import requests

import ml.graph.prose_extraction as prose_extraction
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


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload


def test_extract_facts_degrades_to_empty_on_connection_error(monkeypatch):
    def raise_connection_error(*args, **kwargs):
        raise requests.ConnectionError("Ollama is not running")

    monkeypatch.setattr(prose_extraction.requests, "post", raise_connection_error)

    assert extract_facts("some text") == {"medications": [], "conditions": [], "observations": []}


def test_extract_facts_degrades_to_empty_when_response_key_missing(monkeypatch):
    # Malformed Ollama response body (missing the "response" key) --
    # response.json()["response"] would raise KeyError uncaught before
    # this fix.
    monkeypatch.setattr(prose_extraction.requests, "post", lambda *a, **k: _FakeResponse({}))

    assert extract_facts("some text") == {"medications": [], "conditions": [], "observations": []}


def test_extract_facts_degrades_to_empty_when_response_is_not_valid_json(monkeypatch):
    monkeypatch.setattr(
        prose_extraction.requests, "post",
        lambda *a, **k: _FakeResponse({"response": "not json at all"}),
    )

    assert extract_facts("some text") == {"medications": [], "conditions": [], "observations": []}


def test_extract_facts_degrades_to_empty_when_parsed_json_is_not_an_object(monkeypatch):
    # Schema-constrained decoding should prevent this, but don't trust
    # that blindly -- a bare JSON array/number would otherwise crash on
    # parsed.get(...).
    monkeypatch.setattr(
        prose_extraction.requests, "post",
        lambda *a, **k: _FakeResponse({"response": json.dumps([1, 2, 3])}),
    )

    assert extract_facts("some text") == {"medications": [], "conditions": [], "observations": []}
