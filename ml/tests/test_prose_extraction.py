"""
Tests for ml/graph/prose_extraction.py: a live integration test against
the real qwen3.5:9b model (the winning candidate from
ml/graph/experiments/RESULTS.md) for the happy path, plus mocked-failure
tests for the error-handling contract (no network needed there — the
point is verifying extract_facts() degrades to empty facts on any
failure, not retesting the model itself).
"""

import json

import pytest
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


def test_extract_facts_refuses_a_non_localhost_host(monkeypatch):
    # A misconfigured OLLAMA_HOST must fail loudly (raise), not silently
    # degrade to empty facts and not send clinical note text off-box --
    # this is PHIRE's core "no cloud APIs, no external LLM calls, ever"
    # invariant, and extract_facts runs on the most PHI-sensitive text in
    # the codebase (free-text clinical notes). require_localhost's
    # ValueError is deliberately outside the except clause's caught
    # exception types (requests.RequestException, KeyError,
    # json.JSONDecodeError) so it can't be swallowed like a normal
    # network/parse failure.
    monkeypatch.setattr(prose_extraction, "OLLAMA_HOST", "http://evil.example:11434")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("requests.post must not be called for a non-localhost host")

    monkeypatch.setattr(prose_extraction.requests, "post", fail_if_called)

    with pytest.raises(ValueError, match="localhost"):
        extract_facts("some text")


def test_extract_facts_refuses_localhost_lookalike_hostname(monkeypatch):
    # The exact bypass require_localhost itself was built to close (see
    # test_local_only.py): a hostname that merely starts with/contains
    # "localhost" without actually resolving there.
    monkeypatch.setattr(prose_extraction, "OLLAMA_HOST", "http://localhost.attacker.example:11434")

    with pytest.raises(ValueError, match="localhost"):
        extract_facts("some text")
