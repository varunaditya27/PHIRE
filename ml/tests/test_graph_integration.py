"""
Integration test for ml/graph/observations.py's write path against a real
local Neo4j instance (see ml/.env.example for how to start one) — the
extraction logic itself is tested without Neo4j in test_observations.py.

Writes to and cleans up its own isolated test data (a dedicated patient_id
namespace), doesn't touch "self" or any other real data in the graph.
"""

import pytest

from ml.graph.client import GraphClient
from ml.graph.observations import extract_observations, write_observations

TEST_PATIENT_ID = "test_patient_graph_integration"

TABLE_HTML = (
    "<table>\n"
    "<tr><th>Test</th><th>Result</th><th>Reference Range</th><th>Flag</th></tr>\n"
    "<tr><td>Potassium</td><td>5.4 mEq/L</td><td>3.5-5.0</td><td>High</td></tr>\n"
    "</table>"
)


@pytest.fixture
def graph_client():
    client = GraphClient()
    yield client
    client.run("MATCH (p:Patient {id: $id})-[*0..2]-(n) DETACH DELETE p, n", id=TEST_PATIENT_ID)
    client.close()


def test_write_and_read_back_observation(graph_client):
    text = f"Riverside Medical Group\nDate of Service: 2026-03-01\n\n{TABLE_HTML}"
    observations = extract_observations(text, document_id="integration_doc")

    write_observations(graph_client, "integration_doc", "test.pdf", observations, patient_id=TEST_PATIENT_ID)

    rows = graph_client.run(
        "MATCH (p:Patient {id: $patient_id})-[:HAS_OBSERVATION]->(o:Observation)-[:FROM_DOCUMENT]->(d:Document) "
        "RETURN o.test_name AS test_name, o.value AS value, o.unit AS unit, d.filename AS filename",
        patient_id=TEST_PATIENT_ID,
    )

    assert rows == [{"test_name": "Potassium", "value": 5.4, "unit": "mEq/L", "filename": "test.pdf"}]


def test_reingesting_same_document_updates_not_duplicates(graph_client):
    text = f"Riverside Medical Group\nDate of Service: 2026-03-01\n\n{TABLE_HTML}"
    observations = extract_observations(text, document_id="integration_doc")

    write_observations(graph_client, "integration_doc", "test.pdf", observations, patient_id=TEST_PATIENT_ID)
    write_observations(graph_client, "integration_doc", "test.pdf", observations, patient_id=TEST_PATIENT_ID)

    rows = graph_client.run(
        "MATCH (p:Patient {id: $patient_id})-[:HAS_OBSERVATION]->(o:Observation) RETURN count(o) AS n",
        patient_id=TEST_PATIENT_ID,
    )
    assert rows == [{"n": 1}]
