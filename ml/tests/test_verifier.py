"""
Unit tests for ml/claims/verifier.py's evidence-selection and status-
thresholding logic. Uses a stub subclass that skips loading the real NLI
model (no network/GPU dependency) and injects fixed predictions.
"""

from ml.claims.verifier import ClaimVerifier
from ml.rag.retriever import Chunk


class StubVerifier(ClaimVerifier):
    """ClaimVerifier with fixed per-chunk-id predictions, no model loaded."""

    def __init__(self, predictions: dict[str, dict[str, float]]) -> None:
        self._predictions = predictions

    def _predict(self, premise: str, hypothesis: str) -> dict[str, float]:
        return self._predictions[premise]


def test_verify_returns_unsupported_when_no_evidence():
    verifier = StubVerifier({})
    result = verifier.verify("claim", [])
    assert result.status == "UNSUPPORTED"
    assert result.evidence is None


def test_verify_returns_supported_above_entailment_threshold():
    chunk = Chunk(id="a", text="evidence text", metadata={})
    verifier = StubVerifier({"evidence text": {"entailment": 0.9, "neutral": 0.08, "contradiction": 0.02}})

    result = verifier.verify("claim", [chunk])

    assert result.status == "SUPPORTED"
    assert result.evidence.id == "a"


def test_verify_returns_conflicting_above_contradiction_threshold():
    chunk = Chunk(id="a", text="evidence text", metadata={})
    verifier = StubVerifier({"evidence text": {"entailment": 0.05, "neutral": 0.15, "contradiction": 0.8}})

    result = verifier.verify("claim", [chunk])

    assert result.status == "CONFLICTING"


def test_verify_returns_uncertain_below_both_thresholds():
    chunk = Chunk(id="a", text="evidence text", metadata={})
    verifier = StubVerifier({"evidence text": {"entailment": 0.4, "neutral": 0.5, "contradiction": 0.1}})

    result = verifier.verify("claim", [chunk])

    assert result.status == "UNCERTAIN"


def test_verify_picks_most_informative_chunk_over_a_neutral_one():
    neutral_chunk = Chunk(id="neutral", text="neutral text", metadata={})
    entailing_chunk = Chunk(id="entails", text="entailing text", metadata={})
    verifier = StubVerifier({
        "neutral text": {"entailment": 0.1, "neutral": 0.85, "contradiction": 0.05},
        "entailing text": {"entailment": 0.92, "neutral": 0.05, "contradiction": 0.03},
    })

    result = verifier.verify("claim", [neutral_chunk, entailing_chunk])

    assert result.evidence.id == "entails"
    assert result.status == "SUPPORTED"


def test_verify_entailing_chunk_beats_contradiction_from_unrelated_chunk():
    # Regression: same-template sentences about a different metric (HDL vs an
    # LDL claim) score ~1.0 "contradiction" under NLI and used to outrank the
    # true 0.99-entailing match, flipping a correct claim to CONFLICTING.
    evidence = [Chunk(id="unrelated", text="unrelated text", metadata={}), Chunk(id="match", text="matching text", metadata={})]
    verifier = StubVerifier({
        "unrelated text": {"entailment": 0.0, "neutral": 0.0, "contradiction": 1.0},
        "matching text": {"entailment": 0.99, "neutral": 0.01, "contradiction": 0.0},
    })
    result = verifier.verify("claim", evidence)
    assert result.status == "SUPPORTED"
    assert result.evidence.id == "match"
