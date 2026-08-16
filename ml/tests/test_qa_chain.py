"""
Unit tests for ml/chains/qa_chain.py's orchestration: which claims make it
into the final answer vs. get abstained from. Every subsystem is faked —
this tests QAChain's own wiring/composition logic, not retrieval,
generation, or verification quality (those are tested in their own
modules).
"""

from ml.claims.verifier import ClaimVerification
from ml.chains.qa_chain import NO_EVIDENCE_MESSAGE, QAChain
from ml.rag.retriever import Chunk

EVIDENCE = [Chunk(id="e1", text="evidence", metadata={
    "authority": 0.8, "url": "https://example.com/e1", "char_start": 10, "char_end": 18,
})]


class FakeRetriever:
    def retrieve(self, query, top_k):
        return EVIDENCE


class FakeReranker:
    def rerank(self, query, chunks, top_k):
        return chunks[:top_k]


class FakeExtractor:
    def __init__(self, claims):
        self._claims = claims

    def extract(self, answer):
        return self._claims


class FakeVerifier:
    def __init__(self, verdicts: dict[str, ClaimVerification]):
        self._verdicts = verdicts

    def verify(self, claim, evidence):
        return self._verdicts[claim]


class FakeLLM:
    def generate(self, prompt, **kwargs):
        return "draft answer text"


def build_chain(claims, verdicts) -> QAChain:
    return QAChain(
        retriever=FakeRetriever(),
        reranker=FakeReranker(),
        extractor=FakeExtractor(claims),
        verifier=FakeVerifier(verdicts),
        llm_client=FakeLLM(),
    )


def test_answer_includes_only_supported_high_confidence_claims():
    claims = ["Supported claim.", "Conflicting claim.", "Uncertain claim."]
    verdicts = {
        "Supported claim.": ClaimVerification("Supported claim.", "SUPPORTED", 0.9, 0.0, EVIDENCE[0]),
        "Conflicting claim.": ClaimVerification("Conflicting claim.", "CONFLICTING", 0.05, 0.9, EVIDENCE[0]),
        "Uncertain claim.": ClaimVerification("Uncertain claim.", "UNCERTAIN", 0.4, 0.1, EVIDENCE[0]),
    }
    chain = build_chain(claims, verdicts)

    response = chain.answer("question")

    assert response.answer == "Supported claim."
    assert len(response.claims) == 3  # full audit trail retained even for dropped claims


def test_answer_falls_back_to_no_evidence_message_when_nothing_supported():
    claims = ["Conflicting claim."]
    verdicts = {"Conflicting claim.": ClaimVerification("Conflicting claim.", "CONFLICTING", 0.05, 0.9, EVIDENCE[0])}
    chain = build_chain(claims, verdicts)

    response = chain.answer("question")

    assert response.answer == NO_EVIDENCE_MESSAGE


def test_verified_claim_carries_source_url_from_evidence():
    claims = ["Supported claim."]
    verdicts = {"Supported claim.": ClaimVerification("Supported claim.", "SUPPORTED", 0.9, 0.0, EVIDENCE[0])}
    chain = build_chain(claims, verdicts)

    response = chain.answer("question")

    assert response.claims[0].source_url == "https://example.com/e1"


def test_verified_claim_carries_source_span_from_evidence():
    claims = ["Supported claim."]
    verdicts = {"Supported claim.": ClaimVerification("Supported claim.", "SUPPORTED", 0.9, 0.0, EVIDENCE[0])}
    chain = build_chain(claims, verdicts)

    response = chain.answer("question")

    assert response.claims[0].source_span == (10, 18)


def test_verified_claim_has_no_source_span_when_evidence_lacks_offsets():
    no_span_evidence = Chunk(id="e2", text="evidence", metadata={"authority": 0.8})
    claims = ["Supported claim."]
    verdicts = {"Supported claim.": ClaimVerification("Supported claim.", "SUPPORTED", 0.9, 0.0, no_span_evidence)}
    chain = build_chain(claims, verdicts)

    response = chain.answer("question")

    assert response.claims[0].source_span is None
