"""
Integration test for ml/graph's write path (Observation, Medication,
Condition) against a real local Neo4j instance (see ml/.env.example for
how to start one) — extraction/build logic itself is tested without
Neo4j in test_observations.py.

Writes to and cleans up its own isolated test data (a dedicated patient_id
namespace), doesn't touch "self" or any other real data in the graph.
"""

import pytest
from neo4j.exceptions import ServiceUnavailable

from ml.graph.client import GraphClient
from ml.graph.conditions import build_conditions, write_conditions
from ml.graph.medications import build_medications, write_medications
from ml.graph.observations import build_table_observations, write_observations
from ml.graph.patient_context import get_current_patient_facts, get_patient_facts, get_trend_facts

TEST_PATIENT_ID = "test_patient_graph_integration"

TABLE_HTML = (
    "<table>\n"
    "<tr><th>Test</th><th>Result</th><th>Reference Range</th><th>Flag</th></tr>\n"
    "<tr><td>Potassium</td><td>5.4 mEq/L</td><td>3.5-5.0</td><td>High</td></tr>\n"
    "</table>"
)


@pytest.fixture
def graph_client():
    # Skip (not error) when no local Neo4j is reachable -- without this, a
    # fresh clone or a CI run without Neo4j running fails every test in
    # this file with a raw connection traceback, which reads as
    # unrelated infra noise rather than "this coverage didn't run" (found
    # via review: this file's tests are the only coverage for
    # conditions.py/medications.py/patient_context.py's write and read
    # paths, so a silent skip-that-looks-like-a-pass or an error dismissed
    # as noise both hide a real gap).
    client = GraphClient()
    try:
        client.run("RETURN 1")
    except ServiceUnavailable as exc:
        client.close()
        pytest.skip(f"Neo4j not reachable at {client.uri} -- skipping graph integration tests: {exc}")
    yield client
    client.run("MATCH (p:Patient {id: $id})-[*0..2]-(n) DETACH DELETE p, n", id=TEST_PATIENT_ID)
    client.close()


def test_write_and_read_back_observation(graph_client):
    text = f"Riverside Medical Group\nDate of Service: 2026-03-01\n\n{TABLE_HTML}"
    observations = build_table_observations(text, document_id="integration_doc")

    write_observations(graph_client, "integration_doc", "test.pdf", observations, patient_id=TEST_PATIENT_ID)

    rows = graph_client.run(
        "MATCH (p:Patient {id: $patient_id})-[:HAS_OBSERVATION]->(o:Observation)-[:FROM_DOCUMENT]->(d:Document) "
        "RETURN o.code AS code, o.value AS value, o.unit AS unit, d.filename AS filename",
        patient_id=TEST_PATIENT_ID,
    )

    assert rows == [{"code": "Potassium", "value": 5.4, "unit": "mEq/L", "filename": "test.pdf"}]


def test_reingesting_same_document_updates_not_duplicates(graph_client):
    text = f"Riverside Medical Group\nDate of Service: 2026-03-01\n\n{TABLE_HTML}"
    observations = build_table_observations(text, document_id="integration_doc")

    write_observations(graph_client, "integration_doc", "test.pdf", observations, patient_id=TEST_PATIENT_ID)
    write_observations(graph_client, "integration_doc", "test.pdf", observations, patient_id=TEST_PATIENT_ID)

    rows = graph_client.run(
        "MATCH (p:Patient {id: $patient_id})-[:HAS_OBSERVATION]->(o:Observation) RETURN count(o) AS n",
        patient_id=TEST_PATIENT_ID,
    )
    assert rows == [{"n": 1}]


def test_write_and_read_back_medication(graph_client):
    text = "Progress Note\nDate: 2026-03-01\n\nPlan: increase lisinopril to 20mg daily."
    raw = [{"name": "lisinopril", "dosage": "20mg", "frequency": "daily", "status": "started"}]
    medications = build_medications(raw, text, document_id="integration_doc")

    write_medications(graph_client, "integration_doc", "note.jpg", medications, patient_id=TEST_PATIENT_ID)

    rows = graph_client.run(
        "MATCH (p:Patient {id: $patient_id})-[:HAS_MEDICATION]->(m:Medication)-[:FROM_DOCUMENT]->(d:Document) "
        "RETURN m.code AS code, m.dosage AS dosage, m.status AS status, d.filename AS filename",
        patient_id=TEST_PATIENT_ID,
    )

    assert rows == [{"code": "lisinopril", "dosage": "20mg", "status": "started", "filename": "note.jpg"}]


def test_write_and_read_back_condition(graph_client):
    text = "Progress Note\nDate: 2026-03-01\n\nFollow-up of hypertension."
    raw = [{"name": "hypertension", "status": "active"}]
    conditions = build_conditions(raw, text, document_id="integration_doc")

    write_conditions(graph_client, "integration_doc", "note.jpg", conditions, patient_id=TEST_PATIENT_ID)

    rows = graph_client.run(
        "MATCH (p:Patient {id: $patient_id})-[:HAS_CONDITION]->(c:Condition)-[:FROM_DOCUMENT]->(d:Document) "
        "RETURN c.code AS code, c.status AS status, d.filename AS filename",
        patient_id=TEST_PATIENT_ID,
    )

    assert rows == [{"code": "hypertension", "status": "active", "filename": "note.jpg"}]


def test_get_patient_facts_reads_back_everything_as_sentences(graph_client):
    observations = build_table_observations(
        f"Riverside Medical Group\nDate of Service: 2026-03-01\n\n{TABLE_HTML}", document_id="integration_doc",
    )
    write_observations(graph_client, "integration_doc", "test.pdf", observations, patient_id=TEST_PATIENT_ID)
    medications = build_medications(
        [{"name": "lisinopril", "dosage": "20mg", "frequency": "daily", "status": "started"}],
        "Plan: increase lisinopril to 20mg daily.", document_id="integration_doc",
    )
    write_medications(graph_client, "integration_doc", "note.jpg", medications, patient_id=TEST_PATIENT_ID)
    conditions = build_conditions(
        [{"name": "hypertension", "status": "active"}], "Follow-up of hypertension.", document_id="integration_doc",
    )
    write_conditions(graph_client, "integration_doc", "note.jpg", conditions, patient_id=TEST_PATIENT_ID)

    facts = get_patient_facts(graph_client, patient_id=TEST_PATIENT_ID)

    assert "Potassium: 5.4 mEq/L (reference range 3.5-5.0) -- High on 2026-03-01." in facts
    assert "Medication: lisinopril 20mg daily (started)." in facts
    assert "Condition: hypertension (active)." in facts


def test_get_patient_facts_empty_for_unknown_patient(graph_client):
    assert get_patient_facts(graph_client, patient_id="no_such_patient") == []


def test_get_current_patient_facts_keeps_only_latest_value_per_metric(graph_client):
    # Same lab test recorded twice for this patient, different dates and
    # values -- get_patient_facts should show both (full history for
    # generation); get_current_patient_facts should show only the newer
    # one (single current value for verification).
    older = build_table_observations(
        "<table><tr><th>Test</th><th>Result</th></tr><tr><td>LDL</td><td>191 mg/dL</td></tr></table>",
        document_id="doc_older", effective_date="2026-03-01",
    )
    newer = build_table_observations(
        "<table><tr><th>Test</th><th>Result</th></tr><tr><td>LDL Cholesterol</td><td>162 mg/dL</td></tr></table>",
        document_id="doc_newer", effective_date="2026-03-10",
    )
    write_observations(graph_client, "doc_older", "old.pdf", older, patient_id=TEST_PATIENT_ID)
    write_observations(graph_client, "doc_newer", "new.pdf", newer, patient_id=TEST_PATIENT_ID)

    full_history = get_patient_facts(graph_client, patient_id=TEST_PATIENT_ID)
    current_only = get_current_patient_facts(graph_client, patient_id=TEST_PATIENT_ID)

    assert sum("LDL Cholesterol" in f for f in full_history) == 2
    assert sum("LDL Cholesterol" in f for f in current_only) == 1
    assert "162 mg/dL" in current_only[0]


def test_get_trend_facts_computes_change_between_latest_two_readings(graph_client):
    older = build_table_observations(
        "<table><tr><th>Test</th><th>Result</th></tr><tr><td>LDL</td><td>191 mg/dL</td></tr></table>",
        document_id="doc_older", effective_date="2025-03-01",
    )
    newer = build_table_observations(
        "<table><tr><th>Test</th><th>Result</th></tr><tr><td>LDL Cholesterol</td><td>162 mg/dL</td></tr></table>",
        document_id="doc_newer", effective_date="2026-03-10",
    )
    write_observations(graph_client, "doc_older", "old.pdf", older, patient_id=TEST_PATIENT_ID)
    write_observations(graph_client, "doc_newer", "new.pdf", newer, patient_id=TEST_PATIENT_ID)

    trends = get_trend_facts(graph_client, patient_id=TEST_PATIENT_ID)

    assert len(trends) == 1
    assert "LDL Cholesterol" in trends[0]
    assert "decrease of 29.0" in trends[0]


def test_get_trend_facts_empty_when_metric_has_only_one_reading(graph_client):
    observations = build_table_observations(
        "<table><tr><th>Test</th><th>Result</th></tr><tr><td>Sodium</td><td>138 mEq/L</td></tr></table>",
        document_id="doc_solo", effective_date="2026-03-01",
    )
    write_observations(graph_client, "doc_solo", "solo.pdf", observations, patient_id=TEST_PATIENT_ID)

    assert get_trend_facts(graph_client, patient_id=TEST_PATIENT_ID) == []
