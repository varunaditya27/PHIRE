"""
Unit tests for ml/rag/ingest/patient_documents.py's text extraction, using
a small synthetic PDF fixture (ml/tests/fixtures/sample_lab_report.pdf) —
real pypdf extraction, no mocks, since parsing correctness is the actual
thing worth testing here.
"""

from pathlib import Path

import pytest

from ml.rag.ingest.patient_documents import PDFTextExtractor, extract_text

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "sample_lab_report.pdf"


def test_pdf_extractor_supports_pdf_files():
    extractor = PDFTextExtractor()
    assert extractor.supports(Path("report.pdf")) is True
    assert extractor.supports(Path("report.PDF")) is True
    assert extractor.supports(Path("report.jpg")) is False


def test_pdf_extractor_extracts_text_content():
    text = PDFTextExtractor().extract(FIXTURE_PATH)
    assert "LDL Cholesterol: 162 mg/dL" in text
    assert "Fasting Glucose: 128 mg/dL" in text


def test_extract_text_routes_to_matching_extractor():
    text = extract_text(FIXTURE_PATH)
    assert "PHIRE Test Clinic" in text


def test_extract_text_raises_for_unsupported_format():
    with pytest.raises(ValueError, match="No extractor"):
        extract_text(Path("report.docx"))
