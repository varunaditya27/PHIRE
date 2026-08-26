"""
Unit tests for ml/graph/conditions.py: build_conditions is pure (no Neo4j
dependency, covered here); write_conditions is covered here against a
fake in-memory GraphClient stand-in so its Cypher/param-passing contract
has coverage that doesn't require a live Neo4j (see test_graph_integration.py
for the live round-trip through a real database).
"""

from ml.graph.conditions import build_conditions, write_conditions


class _FakeGraphClient:
    """Records every run() call instead of talking to Neo4j."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def run(self, query: str, **params) -> list[dict]:
        self.calls.append((query, params))
        return []


def test_build_conditions_attaches_id_and_effective_date():
    raw = [{"name": "hypertension", "status": "active"}]

    result = build_conditions(raw, "Follow-up of hypertension.", document_id="doc1", effective_date="2026-03-01")

    assert result == [{"id": "doc1:hypertension", "code": "hypertension", "status": "active", "effective": "2026-03-01"}]


def test_build_conditions_defaults_missing_status_to_unspecified():
    raw = [{"name": "seasonal allergies"}]

    result = build_conditions(raw, "no date here", document_id="doc1", effective_date="2026-03-01")

    assert result[0]["status"] == "unspecified"


def test_build_conditions_skips_entries_missing_name():
    raw = [{"status": "active"}, {"name": "hypertension", "status": "active"}]

    result = build_conditions(raw, "text", document_id="doc1", effective_date="2026-03-01")

    assert len(result) == 1
    assert result[0]["code"] == "hypertension"


def test_build_conditions_scans_document_text_when_no_effective_date_passed():
    raw = [{"name": "hypertension", "status": "active"}]

    result = build_conditions(raw, "Date of Service: 2026-03-01\nFollow-up.", document_id="doc1")

    assert result[0]["effective"] == "2026-03-01"


def test_build_conditions_ids_are_stable_and_lowercased():
    raw = [{"name": "Type 2 Diabetes", "status": "active"}]

    result = build_conditions(raw, "text", document_id="doc1", effective_date="2026-03-01")

    assert result[0]["id"] == "doc1:type_2_diabetes"


def test_write_conditions_skips_the_query_entirely_for_an_empty_list():
    client = _FakeGraphClient()

    write_conditions(client, "doc1", "note.jpg", [], patient_id="self")

    assert client.calls == []


def test_write_conditions_passes_patient_document_and_condition_params():
    client = _FakeGraphClient()
    conditions = [{"id": "doc1:hypertension", "code": "hypertension", "status": "active", "effective": "2026-03-01"}]

    write_conditions(client, "doc1", "note.jpg", conditions, patient_id="self")

    assert len(client.calls) == 1
    query, params = client.calls[0]
    assert "MERGE (c:Condition {id: cond.id})" in query
    assert "HAS_CONDITION" in query
    assert params == {
        "patient_id": "self", "document_id": "doc1", "filename": "note.jpg", "conditions": conditions,
    }
