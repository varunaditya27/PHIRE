"""
Live end-to-end test of ml/chains/qa_chain.py's full pipeline: real
Chroma/BM25 retrieval over the actual ingested reference corpus, real
MedCPT reranking, real Ollama generation (medgemma:4b), real BART-large-
MNLI claim verification, and real Neo4j-backed patient facts/trends --
no fakes anywhere, unlike test_qa_chain.py's orchestration-only unit
tests.

Everything runs against an isolated test patient id, never "self" (the
real single-patient namespace this repo runs against -- see
ml/graph/observations.py's module docstring). QAChain always reads/writes
"self" internally (ml/graph/patient_context.py's DEFAULT_PATIENT_ID), so
this monkeypatches the three patient-context functions qa_chain imports
to bind to TEST_PATIENT_ID instead, then exercises the real, unmodified
QAChain.answer() code path -- not a reimplementation of it.

Slow (loads 3 local models onto the GPU + calls Ollama) and skipped
outright if Neo4j isn't reachable -- this is a deliberate, occasional
live smoke test, not part of the fast unit-test loop.

Content assertions check claim *grounding* (source_url and source_filename
both None -- see _grounded_claims), not substrings of the model's free-form
prose. Found necessary live, not by inspection: the real data/chroma
reference corpus already contains 21 chunks from earlier OCR-benchmark
fixture ingestion (cmp_table_photo.jpg, progress_note_photo.jpg,
sample_lab_report.pdf -- a synthetic "R. Thompson" patient), tagged
source=patient_document, authority=1.0 -- the same authority tier as this
test's own seeded facts. Those fixtures happen to share this test's exact
LDL value (162 mg/dL) and medication (lisinopril), and one is itself a
comprehensive metabolic panel with a Potassium row -- so a plain substring
match in response.answer can pass even when the claim that produced it
was never grounded in this test's own seeded patient data at all. Only a
claim verified against a patient_record/patient_derived chunk (built by
ml.chains.qa_chain._facts_to_chunks, which never sets url/filename
metadata) has both fields None; a claim grounded in any real ingested
document -- including a same-authority decoy -- always has one set.
"""

import pytest
from neo4j.exceptions import ServiceUnavailable

from ml.chains.qa_chain import QAChain
from ml.claims.verifier import ClaimVerifier
from ml.graph.client import GraphClient
from ml.graph.conditions import build_conditions, write_conditions
from ml.graph.medications import build_medications, write_medications
from ml.graph.observations import build_table_observations, write_observations
from ml.graph.patient_context import get_current_patient_facts, get_patient_facts, get_trend_facts
from ml.llm.ollama_client import OllamaClient
from ml.rag.reranker import Reranker
from ml.rag.retriever import HybridRetriever

TEST_PATIENT_ID = "test_patient_qa_chain_live_e2e"

LDL_TABLE_OLDER = (
    "<table><tr><th>Test</th><th>Result</th></tr>"
    "<tr><td>LDL Cholesterol</td><td>191 mg/dL</td></tr></table>"
)
LDL_TABLE_NEWER = (
    "<table><tr><th>Test</th><th>Result</th></tr>"
    "<tr><td>LDL Cholesterol</td><td>162 mg/dL</td></tr></table>"
)
POTASSIUM_TABLE = (
    "<table><tr><th>Test</th><th>Result</th><th>Reference Range</th><th>Flag</th></tr>"
    "<tr><td>Potassium</td><td>7.9 mEq/L</td><td>3.5-5.0</td><td>Critical High</td></tr></table>"
)


@pytest.fixture(scope="module")
def graph_client():
    client = GraphClient()
    try:
        client.run("RETURN 1")
    except ServiceUnavailable as exc:
        client.close()
        pytest.skip(f"Neo4j not reachable at {client.uri} -- skipping live QAChain E2E: {exc}")
    yield client
    client.run("MATCH (p:Patient {id: $id})-[*0..2]-(n) DETACH DELETE p, n", id=TEST_PATIENT_ID)
    client.close()


@pytest.fixture(scope="module")
def seeded_patient(graph_client):
    """Write a small but realistic patient history: a trend, an out-of-range value, a med, a condition."""
    older = build_table_observations(LDL_TABLE_OLDER, document_id="doc_older", effective_date="2025-03-01")
    newer = build_table_observations(LDL_TABLE_NEWER, document_id="doc_newer", effective_date="2026-03-10")
    critical = build_table_observations(POTASSIUM_TABLE, document_id="doc_critical", effective_date="2026-03-10")
    write_observations(graph_client, "doc_older", "old.pdf", older, patient_id=TEST_PATIENT_ID)
    write_observations(graph_client, "doc_newer", "new.pdf", newer, patient_id=TEST_PATIENT_ID)
    write_observations(graph_client, "doc_critical", "crit.pdf", critical, patient_id=TEST_PATIENT_ID)

    medications = build_medications(
        [{"name": "lisinopril", "dosage": "20mg", "frequency": "daily", "status": "started"}],
        "Plan: increase lisinopril to 20mg daily.", document_id="doc_newer", effective_date="2026-03-10",
    )
    write_medications(graph_client, "doc_newer", "new.pdf", medications, patient_id=TEST_PATIENT_ID)

    conditions = build_conditions(
        [{"name": "hypertension", "status": "active"}],
        "Follow-up of hypertension.", document_id="doc_newer", effective_date="2026-03-10",
    )
    write_conditions(graph_client, "doc_newer", "new.pdf", conditions, patient_id=TEST_PATIENT_ID)
    return graph_client


@pytest.fixture(scope="module")
def live_qa_chain(monkeypatch_module_scope, seeded_patient):
    """A real QAChain (no fakes) whose patient-context calls resolve against TEST_PATIENT_ID, not "self"."""
    monkeypatch_module_scope.setattr(
        "ml.chains.qa_chain.get_patient_facts",
        lambda client: get_patient_facts(client, patient_id=TEST_PATIENT_ID),
    )
    monkeypatch_module_scope.setattr(
        "ml.chains.qa_chain.get_current_patient_facts",
        lambda client: get_current_patient_facts(client, patient_id=TEST_PATIENT_ID),
    )
    monkeypatch_module_scope.setattr(
        "ml.chains.qa_chain.get_trend_facts",
        lambda client: get_trend_facts(client, patient_id=TEST_PATIENT_ID),
    )
    return QAChain(
        retriever=HybridRetriever(),
        reranker=Reranker(),
        verifier=ClaimVerifier(),
        llm_client=OllamaClient(),
        graph_client=seeded_patient,
    )


@pytest.fixture(scope="module")
def monkeypatch_module_scope():
    # pytest's built-in monkeypatch fixture is function-scoped; this repo
    # loads 3 GPU models per QAChain, so a module-scoped equivalent is
    # used to build live_qa_chain once for the whole file instead of once
    # per test.
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()


def _grounded_claims(response, keyword: str) -> list:
    """Claims verified against this test's own seeded patient/trend facts (see module docstring), mentioning keyword."""
    return [
        c for c in response.claims
        if c.status in ("SUPPORTED", "DERIVED") and c.source_url is None and c.source_filename is None
        and keyword in c.claim.lower()
    ]


def test_answer_surfaces_a_direct_patient_fact(live_qa_chain):
    response = live_qa_chain.answer("What was my most recent LDL cholesterol result?")

    grounded = _grounded_claims(response, "ldl")
    assert grounded, (
        f"expected a claim grounded in this test's own seeded LDL fact, got: "
        f"{[(c.claim, c.status, c.source_url, c.source_filename) for c in response.claims]}"
    )


def test_answer_reports_the_ldl_trend_as_derived(live_qa_chain):
    response = live_qa_chain.answer("How has my LDL cholesterol changed over time?")

    assert any(c.status == "DERIVED" for c in response.claims), (
        f"expected at least one DERIVED claim, got statuses: {[c.status for c in response.claims]}"
    )


def test_answer_surfaces_the_critical_potassium_value(live_qa_chain):
    response = live_qa_chain.answer("What is my potassium level and is it a concern?")

    # Claim decomposition doesn't always repeat "potassium" verbatim in
    # every atomic claim (e.g. "7.9 mEq/L is a critical high" as a
    # follow-on to a claim that already named it) -- match on the value
    # or the flag too, not just the metric name.
    grounded = (
        _grounded_claims(response, "potassium")
        or _grounded_claims(response, "7.9")
        or _grounded_claims(response, "critical")
    )
    assert grounded, (
        f"expected a claim grounded in this test's own seeded potassium fact, got: "
        f"{[(c.claim, c.status, c.source_url, c.source_filename) for c in response.claims]}"
    )


def test_answer_includes_current_medication(live_qa_chain):
    response = live_qa_chain.answer("What medication am I currently taking?")

    grounded = _grounded_claims(response, "lisinopril")
    assert grounded, (
        f"expected a claim grounded in this test's own seeded medication fact, got: "
        f"{[(c.claim, c.status, c.source_url, c.source_filename) for c in response.claims]}"
    )


def test_answer_abstains_on_a_question_with_no_relevant_evidence(live_qa_chain):
    # Nothing in this patient's record or the reference corpus concerns
    # veterinary medicine -- draft generation may still attempt an answer
    # (the LLM isn't grounded at generation time), but verification should
    # find nothing to support it.
    response = live_qa_chain.answer("What is the recommended deworming schedule for a pet iguana?")

    assert not any(c.status in ("SUPPORTED", "DERIVED") and c.confidence >= 0.4 for c in response.claims), (
        f"expected no confidently-verified claims, got: "
        f"{[(c.claim, c.status, c.confidence) for c in response.claims]}"
    )


def test_answer_every_claim_has_a_confidence_score_in_valid_range(live_qa_chain):
    response = live_qa_chain.answer("Summarize my current health status.")

    assert response.claims, "expected at least one extracted claim from a summary question"
    for claim in response.claims:
        assert 0.0 <= claim.confidence <= 1.0
        assert claim.status in ("SUPPORTED", "DERIVED", "CONFLICTING", "UNCERTAIN", "UNSUPPORTED")
