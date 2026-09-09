from pathlib import Path

from ml.rag.ingest.patient_documents import (
    extract_document_data,
    extract_text,
    supports_document,
)


def test_supports_pdf_and_images():
    assert supports_document(Path("test.pdf"))
    assert supports_document(Path("test.png"))
    assert supports_document(Path("test.jpg"))
    assert not supports_document(Path("test.exe"))


def test_extract_document_data_mock(monkeypatch, tmp_path):
    monkeypatch.setenv("PHIRE_MOCK_LIFT", "true")
    dummy = tmp_path / "sample.pdf"
    dummy.write_bytes(b"%PDF dummy")

    data = extract_document_data(dummy)
    assert len(data["observations"]) > 0
    assert len(data["medications"]) > 0
    assert len(data["conditions"]) > 0


def test_extract_text_backward_compat(monkeypatch, tmp_path):
    monkeypatch.setenv("PHIRE_MOCK_LIFT", "true")
    dummy = tmp_path / "sample.pdf"
    dummy.write_bytes(b"%PDF dummy")

    text = extract_text(dummy)
    assert isinstance(text, str)
    assert "LDL Cholesterol" in text
