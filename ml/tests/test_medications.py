"""
Unit tests for ml/graph/medications.py: build_medications is pure (no
Neo4j dependency, covered here); write_medications is covered here
against a fake in-memory GraphClient stand-in so its Cypher/param-passing
contract has coverage that doesn't require a live Neo4j (see
test_graph_integration.py for the live round-trip through a real
database).
"""

from ml.graph.medications import build_medications, write_medications


class _FakeGraphClient:
    """Records every run() call instead of talking to Neo4j."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def run(self, query: str, **params) -> list[dict]:
        self.calls.append((query, params))
        return []


def test_build_medications_attaches_id_and_effective_date():
    raw = [{"name": "lisinopril", "dosage": "20mg", "frequency": "daily", "status": "started"}]

    result = build_medications(raw, "Plan: increase lisinopril.", document_id="doc1", effective_date="2026-03-01")

    assert result == [{
        "id": "doc1:lisinopril", "code": "lisinopril", "dosage": "20mg", "frequency": "daily",
        "status": "started", "effective": "2026-03-01",
    }]


def test_build_medications_defaults_missing_fields():
    raw = [{"name": "aspirin"}]

    result = build_medications(raw, "text", document_id="doc1", effective_date="2026-03-01")

    assert result[0]["dosage"] is None
    assert result[0]["frequency"] is None
    assert result[0]["status"] == "unspecified"


def test_build_medications_skips_entries_missing_name():
    raw = [{"dosage": "20mg"}, {"name": "lisinopril", "dosage": "20mg"}]

    result = build_medications(raw, "text", document_id="doc1", effective_date="2026-03-01")

    assert len(result) == 1
    assert result[0]["code"] == "lisinopril"


def test_build_medications_scans_document_text_when_no_effective_date_passed():
    raw = [{"name": "lisinopril"}]

    result = build_medications(raw, "Date of Service: 2026-03-01\nPlan.", document_id="doc1")

    assert result[0]["effective"] == "2026-03-01"


def test_build_medications_ids_are_stable_and_lowercased():
    raw = [{"name": "Lisinopril HCTZ"}]

    result = build_medications(raw, "text", document_id="doc1", effective_date="2026-03-01")

    assert result[0]["id"] == "doc1:lisinopril_hctz"


def test_write_medications_skips_the_query_entirely_for_an_empty_list():
    client = _FakeGraphClient()

    write_medications(client, "doc1", "note.jpg", [], patient_id="self")

    assert client.calls == []


def test_write_medications_passes_patient_document_and_medication_params():
    client = _FakeGraphClient()
    medications = [{
        "id": "doc1:lisinopril", "code": "lisinopril", "dosage": "20mg", "frequency": "daily",
        "status": "started", "effective": "2026-03-01",
    }]

    write_medications(client, "doc1", "note.jpg", medications, patient_id="self")

    assert len(client.calls) == 1
    query, params = client.calls[0]
    assert "MERGE (m:Medication {id: med.id})" in query
    assert "HAS_MEDICATION" in query
    assert params == {
        "patient_id": "self", "document_id": "doc1", "filename": "note.jpg", "medications": medications,
    }
