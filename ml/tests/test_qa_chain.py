"""
Unit tests for ml/chains/qa_chain.py's orchestration: which claims make it
into the final answer vs. get abstained from. Every subsystem is faked —
this tests QAChain's own wiring/composition logic, not retrieval,
generation, or verification quality (those are tested in their own
modules).
"""

from ml.claims.verifier import ClaimVerification
from ml.chains.qa_chain import MAX_FACT_EVIDENCE, NO_EVIDENCE_MESSAGE, QAChain
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


class FakeGraphClient:
    """Stands in for GraphClient: get_patient_facts only ever calls .run()."""

    def run(self, query, **params):
        return []


def build_chain(claims, verdicts) -> QAChain:
    return QAChain(
        retriever=FakeRetriever(),
        reranker=FakeReranker(),
        extractor=FakeExtractor(claims),
        verifier=FakeVerifier(verdicts),
        llm_client=FakeLLM(),
        graph_client=FakeGraphClient(),
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


def test_unsupported_claim_with_no_matched_evidence_gets_zero_confidence():
    # verification.evidence is None exactly when ClaimVerifier.verify()'s
    # own pool was empty (see its docstring) -- confidence must reflect
    # "no evidence," not the retrieval-only floor a rank of 0 would give
    # it (found via review: `next(..., len(evidence))`'s old fallback
    # collided with a real rank of 0 for this exact case).
    claims = ["Unsupported claim."]
    verdicts = {"Unsupported claim.": ClaimVerification("Unsupported claim.", "UNSUPPORTED", 0.0, 0.0, None)}
    chain = build_chain(claims, verdicts)

    response = chain.answer("question")

    assert response.claims[0].confidence == 0.0


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


def test_answer_fetches_graph_facts_when_observations_not_given(monkeypatch):
    claims = ["Supported claim."]
    verdicts = {"Supported claim.": ClaimVerification("Supported claim.", "SUPPORTED", 0.9, 0.0, EVIDENCE[0])}
    chain = build_chain(claims, verdicts)

    seen_prompts = []
    monkeypatch.setattr(
        "ml.chains.qa_chain.build_chat_prompt",
        lambda question, evidence, observations: seen_prompts.append(observations) or "prompt",
    )
    monkeypatch.setattr(
        "ml.chains.qa_chain.get_patient_facts", lambda client: ["LDL Cholesterol: 149 mg/dL on 2026-08-14."],
    )

    chain.answer("question")

    assert seen_prompts == [["LDL Cholesterol: 149 mg/dL on 2026-08-14."]]


def test_verify_claim_pool_includes_patient_facts_alongside_reference_evidence(monkeypatch):
    # The bug this fixes: a claim built entirely from a patient observation
    # ("your LDL was 162 mg/dL") had nothing to verify against, because
    # observations never reached the verifier -- only reranked reference
    # chunks did. Confirms patient facts are now in the pool _verify_claim
    # actually checks against.
    claims = ["Supported claim."]
    verdicts = {"Supported claim.": ClaimVerification("Supported claim.", "SUPPORTED", 0.9, 0.0, EVIDENCE[0])}
    seen_pools = []

    class RecordingVerifier:
        def verify(self, claim, evidence):
            seen_pools.append(evidence)
            return verdicts[claim]

    monkeypatch.setattr(
        "ml.chains.qa_chain.get_current_patient_facts_with_sources",
        lambda client: [("LDL Cholesterol: 162 mg/dL on 2026-03-10.", "labs.pdf")],
    )
    chain = QAChain(
        retriever=FakeRetriever(), reranker=FakeReranker(), extractor=FakeExtractor(claims),
        verifier=RecordingVerifier(), llm_client=FakeLLM(), graph_client=FakeGraphClient(),
    )

    chain.answer("question")

    pool_texts = [c.text for c in seen_pools[0]]
    assert "LDL Cholesterol: 162 mg/dL on 2026-03-10." in pool_texts
    assert "evidence" in pool_texts  # the reference chunk is still in the pool too


def test_answer_relabels_supported_trend_claim_as_derived(monkeypatch):
    claim = "My LDL Cholesterol decreased by 29.0 mg/dL."
    verdicts = {claim: ClaimVerification(claim, "SUPPORTED", 0.9, 0.0, None)}  # evidence filled in below

    class RecordingVerifier:
        def verify(self, claim, evidence):
            # Mimic the real verifier: whichever chunk in the pool is the
            # trend fact "wins" (it's the only one relevant to this claim).
            trend_chunk = next(c for c in evidence if c.metadata.get("source") == "patient_derived")
            return ClaimVerification(claim, "SUPPORTED", 0.9, 0.0, trend_chunk)

    monkeypatch.setattr(
        "ml.chains.qa_chain.get_current_patient_facts_with_sources", lambda client: [],
    )
    monkeypatch.setattr(
        "ml.chains.qa_chain.get_trend_facts_with_sources",
        lambda client: [("LDL Cholesterol changed from 191 mg/dL to 162 mg/dL (a decrease of 29.0 mg/dL).", ["jan.pdf", "mar.pdf"])],
    )
    chain = QAChain(
        retriever=FakeRetriever(), reranker=FakeReranker(), extractor=FakeExtractor([claim]),
        verifier=RecordingVerifier(), llm_client=FakeLLM(), graph_client=FakeGraphClient(),
    )

    response = chain.answer("question")

    assert response.claims[0].status == "DERIVED"
    assert response.answer == claim  # DERIVED counts as verified, makes it into the final answer


def test_answer_respects_explicit_observations_override():
    claims = ["Supported claim."]
    verdicts = {"Supported claim.": ClaimVerification("Supported claim.", "SUPPORTED", 0.9, 0.0, EVIDENCE[0])}
    chain = build_chain(claims, verdicts)

    # Doesn't raise even though FakeGraphClient.run() would return []
    # for the auto-fetch path -- passing observations explicitly skips
    # the graph fetch entirely.
    response = chain.answer("question", observations=["explicit fact"])

    assert response.answer == "Supported claim."


def test_answer_degrades_gracefully_when_graph_is_unreachable():
    # CLAUDE.md documents the graph layer as "not MVP-blocking" -- a
    # Neo4j outage shouldn't 502 a question that never needed patient
    # facts (found via review: answer() previously let any GraphClient
    # exception propagate uncaught).
    class BrokenGraphClient:
        def run(self, query, **params):
            raise ConnectionError("Neo4j unreachable")

    claims = ["Supported claim."]
    verdicts = {"Supported claim.": ClaimVerification("Supported claim.", "SUPPORTED", 0.9, 0.0, EVIDENCE[0])}
    chain = QAChain(
        retriever=FakeRetriever(), reranker=FakeReranker(), extractor=FakeExtractor(claims),
        verifier=FakeVerifier(verdicts), llm_client=FakeLLM(), graph_client=BrokenGraphClient(),
    )

    response = chain.answer("question")  # must not raise

    assert response.answer == "Supported claim."


def test_verification_pool_caps_patient_facts_at_max_fact_evidence(monkeypatch):
    # Regression for the unbounded-pool latency risk: ClaimVerifier.verify()
    # runs a full NLI forward pass per pool chunk per claim, so a patient
    # with a long observation history must not push every one of those
    # facts into the pool uncapped.
    claims = ["Supported claim."]
    verdicts = {"Supported claim.": ClaimVerification("Supported claim.", "SUPPORTED", 0.9, 0.0, EVIDENCE[0])}
    seen_pools = []

    class RecordingVerifier:
        def verify(self, claim, evidence):
            seen_pools.append(evidence)
            return verdicts[claim]

    many_facts = [f"Fact number {i}." for i in range(MAX_FACT_EVIDENCE + 25)]
    monkeypatch.setattr(
        "ml.chains.qa_chain.get_current_patient_facts_with_sources", lambda client: [(f, None) for f in many_facts],
    )
    monkeypatch.setattr("ml.chains.qa_chain.get_trend_facts_with_sources", lambda client: [])
    chain = QAChain(
        retriever=FakeRetriever(), reranker=FakeReranker(), extractor=FakeExtractor(claims),
        verifier=RecordingVerifier(), llm_client=FakeLLM(), graph_client=FakeGraphClient(),
    )

    chain.answer("question")

    patient_chunks = [c for c in seen_pools[0] if c.metadata.get("source") == "patient_record"]
    assert len(patient_chunks) == MAX_FACT_EVIDENCE


def test_verification_pool_caps_trend_facts_independently_of_patient_facts(monkeypatch):
    # Each list is capped on its own -- a long trend-fact list shouldn't
    # crowd out patient facts (or vice versa) since they're capped before
    # being combined into one pool.
    claims = ["Supported claim."]
    verdicts = {"Supported claim.": ClaimVerification("Supported claim.", "SUPPORTED", 0.9, 0.0, EVIDENCE[0])}
    seen_pools = []

    class RecordingVerifier:
        def verify(self, claim, evidence):
            seen_pools.append(evidence)
            return verdicts[claim]

    many_trends = [f"Trend number {i}." for i in range(MAX_FACT_EVIDENCE + 10)]
    few_facts = ["LDL Cholesterol: 162 mg/dL on 2026-03-10."]
    monkeypatch.setattr(
        "ml.chains.qa_chain.get_current_patient_facts_with_sources", lambda client: [(f, None) for f in few_facts],
    )
    monkeypatch.setattr(
        "ml.chains.qa_chain.get_trend_facts_with_sources", lambda client: [(t, []) for t in many_trends],
    )
    chain = QAChain(
        retriever=FakeRetriever(), reranker=FakeReranker(), extractor=FakeExtractor(claims),
        verifier=RecordingVerifier(), llm_client=FakeLLM(), graph_client=FakeGraphClient(),
    )

    chain.answer("question")

    pool = seen_pools[0]
    assert len([c for c in pool if c.metadata.get("source") == "patient_derived"]) == MAX_FACT_EVIDENCE
    assert len([c for c in pool if c.metadata.get("source") == "patient_record"]) == len(few_facts)


def test_verified_claim_has_no_source_span_when_evidence_lacks_offsets():
    # no_span_evidence must actually be part of the pool passed to
    # verify() (a custom reranker returning it, not the module-level
    # EVIDENCE/build_chain default), not just the FakeVerifier's canned
    # return value -- _verify_claim looks up the matched chunk's rank
    # within that pool by identity, same as the real ClaimVerifier
    # guarantees (found via review: this test previously papered over
    # that by returning a chunk id absent from the actual pool, which
    # only worked because of the very rank-lookup bug being fixed).
    no_span_evidence = Chunk(id="e2", text="evidence", metadata={"authority": 0.8})
    claims = ["Supported claim."]
    verdicts = {"Supported claim.": ClaimVerification("Supported claim.", "SUPPORTED", 0.9, 0.0, no_span_evidence)}

    class NoSpanReranker:
        def rerank(self, query, chunks, top_k):
            return [no_span_evidence]

    chain = QAChain(
        retriever=FakeRetriever(), reranker=NoSpanReranker(), extractor=FakeExtractor(claims),
        verifier=FakeVerifier(verdicts), llm_client=FakeLLM(), graph_client=FakeGraphClient(),
    )

    response = chain.answer("question")

    assert response.claims[0].source_span is None


def test_answer_reports_each_stage_in_order_via_on_progress():
    claims = ["Claim A.", "Claim B."]
    verdicts = {c: ClaimVerification(c, "SUPPORTED", 0.9, 0.0, EVIDENCE[0]) for c in claims}
    events: list[tuple[str, str]] = []

    build_chain(claims, verdicts).answer("question", on_progress=lambda stage, msg: events.append((stage, msg)))

    assert [stage for stage, _ in events] == ["graph", "retrieve", "generate", "extract", "verify", "verify"]
    assert events[-1][1].startswith("Verifying claim 2 of 2")


def test_answer_exposes_the_retrieved_evidence_for_citations():
    claims = ["Supported claim."]
    verdicts = {"Supported claim.": ClaimVerification("Supported claim.", "SUPPORTED", 0.9, 0.0, EVIDENCE[0])}

    response = build_chain(claims, verdicts).answer("question")

    assert response.evidence == EVIDENCE


def test_facts_to_chunks_attaches_source_filename_when_known():
    chunks = QAChain._facts_to_chunks(["a", "b"], source="patient_record", filenames=[["labs.pdf"], []])

    assert chunks[0].metadata["filenames"] == ["labs.pdf"]
    assert "filenames" not in chunks[1].metadata


def test_trend_claim_cites_every_source_document():
    claim = "LDL decreased by 29 mg/dL."
    trend = "LDL Cholesterol changed from 191 mg/dL to 162 mg/dL (a decrease of 29.0 mg/dL)."

    class TrendVerifier:
        def verify(self, claim, evidence):
            chunk = next(c for c in evidence if c.metadata.get("source") == "patient_derived")
            return ClaimVerification(claim, "SUPPORTED", 0.9, 0.0, chunk)

    import ml.chains.qa_chain as qa
    original_current, original_trend = qa.get_current_patient_facts_with_sources, qa.get_trend_facts_with_sources
    qa.get_current_patient_facts_with_sources = lambda client: []
    qa.get_trend_facts_with_sources = lambda client: [(trend, ["jan.pdf", "mar.pdf"])]
    try:
        chain = QAChain(
            retriever=FakeRetriever(), reranker=FakeReranker(), extractor=FakeExtractor([claim]),
            verifier=TrendVerifier(), llm_client=FakeLLM(), graph_client=FakeGraphClient(),
        )
        verified = chain.answer("question").claims[0]
    finally:
        qa.get_current_patient_facts_with_sources, qa.get_trend_facts_with_sources = original_current, original_trend

    assert verified.status == "DERIVED"
    assert verified.source_filenames == ["jan.pdf", "mar.pdf"]
    assert verified.source_filename == "jan.pdf"
