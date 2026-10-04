"""
Unit tests for ml/rag/ingest/ingest_patient_document.py's chunk-building
logic, using LiftExtractor mock execution.
"""

from pathlib import Path

import pytest

from ml.rag.ingest.ingest_patient_document import build_chunks

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "sample_lab_report.pdf"


@pytest.fixture(autouse=True)
def mock_lift_env(monkeypatch):
    monkeypatch.setenv("PHIRE_MOCK_LIFT", "true")


class EmptyTextExtractor:
    """Stands in for a scanned/image-only PDF that yields no extractable text."""

    def supports(self, file_path: Path) -> bool:
        return True

    def extract(self, file_path: Path) -> str:
        return ""


def test_build_chunks_wraps_extracted_text_with_patient_document_metadata():
    chunks = build_chunks(FIXTURE_PATH)

    assert len(chunks) >= 1
    assert all(c.metadata["source"] == "patient_document" for c in chunks)
    assert all(c.metadata["authority"] == 1.0 for c in chunks)
    assert all(c.metadata["filename"] == "sample_lab_report.pdf" for c in chunks)
    assert any("LDL Cholesterol" in c.text for c in chunks)


def test_build_chunks_ids_are_stable_across_runs():
    # Same file content -> same document_id (content hash), so re-running
    # ingestion on the same file produces the same chunk ids rather than
    # silently duplicating entries in Chroma.
    first = build_chunks(FIXTURE_PATH)
    second = build_chunks(FIXTURE_PATH)
    assert [c.id for c in first] == [c.id for c in second]


def test_build_chunks_raises_on_empty_extraction():
    with pytest.raises(ValueError, match="No text extracted"):
        build_chunks(FIXTURE_PATH, extractors=[EmptyTextExtractor()])


def test_build_chunks_with_preextracted_data():
    custom_data = {
        "document_date": "2026-04-01",
        "document_type": "Progress Note",
        "observations": [
            {"name": "Systolic BP", "value": "120", "unit": "mmHg"}
        ],
        "medications": [],
        "conditions": [],
        "narrative_sections": [],
    }
    chunks = build_chunks(FIXTURE_PATH, data=custom_data)
    assert len(chunks) == 1
    assert "Systolic BP was 120 mmHg" in chunks[0].text
    assert chunks[0].metadata["document_date"] == "2026-04-01"


def test_build_chunks_with_text_backward_compatibility():
    chunks = build_chunks(FIXTURE_PATH, text="Patient report summary text")
    assert len(chunks) >= 1
    assert any("Patient report summary text" in c.text for c in chunks)


def test_build_chunks_raises_on_empty_data():
    with pytest.raises(ValueError, match="No content extracted"):
        build_chunks(FIXTURE_PATH, data={})
