"""Unit tests for ml/rag/ingest/ollama_extractor.py with a fake Ollama (no model, no network)."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ml.rag.ingest.ollama_extractor import OllamaVisionExtractor, merge_pages
from ml.rag.ingest.lift_schema import CLINICAL_DOCUMENT_SCHEMA

FIXTURE_PDF = Path(__file__).resolve().parent / "fixtures" / "sample_lab_report.pdf"


def fake_post(pages_payloads, calls):
    """A `post` that answers each call with the next canned payload (as Ollama's /api/chat would)."""
    queue = list(pages_payloads)

    def post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        response = MagicMock()
        payload = queue.pop(0)
        response.json.return_value = {"message": {"content": payload if isinstance(payload, str) else __import__("json").dumps(payload)}}
        return response

    return post


PAGE = {"document_date": "12 March 2026", "document_type": "Lab report",
        "observations": [{"name": "LDL Cholesterol", "value": "138", "unit": "mg/dL"}],
        "medications": [{"name": "Atorvastatin", "dosage": "20 mg", "frequency": "daily", "status": "active"}],
        "conditions": [{"name": "Hypercholesterolemia", "status": "active"}], "narrative_sections": []}


def test_extract_sends_a_schema_constrained_request_with_page_image_and_text_layer():
    calls = []
    extractor = OllamaVisionExtractor(post=fake_post([PAGE], calls))

    result = extractor.extract(FIXTURE_PDF)

    request = calls[0]["json"]
    assert request["format"] == CLINICAL_DOCUMENT_SCHEMA            # Ollama grammar-constrains output to the schema
    assert request["options"]["temperature"] == 0 and request["stream"] is False
    message = request["messages"][0]
    assert len(message["images"]) == 1 and "text layer" in message["content"]   # image + the PDF's own text
    assert calls[0]["url"].endswith("/api/chat")
    assert result["observations"][0]["name"] == "LDL Cholesterol" and result["document_date"] == "12 March 2026"


def test_pages_are_merged_without_duplicates_and_first_date_wins():
    page2 = {**PAGE, "document_date": "13 March 2026",
             "observations": [{"name": "LDL Cholesterol", "value": "138", "unit": "mg/dL"}, {"name": "HDL", "value": "46", "unit": "mg/dL"}]}

    merged = merge_pages([PAGE, page2])

    assert merged["document_date"] == "12 March 2026"
    assert [o["name"] for o in merged["observations"]] == ["LDL Cholesterol", "HDL"]   # repeated LDL dropped
    assert len(merged["medications"]) == 1 and len(merged["conditions"]) == 1


def test_an_unreadable_page_contributes_nothing_instead_of_failing_the_document():
    result = OllamaVisionExtractor(post=fake_post(["this is not json"], [])).extract(FIXTURE_PDF)

    assert result["observations"] == [] and result["document_date"] is None


def test_unsupported_and_missing_files_are_rejected(tmp_path):
    extractor = OllamaVisionExtractor(post=fake_post([], []))

    with pytest.raises(ValueError):
        extractor.extract(tmp_path / "notes.txt")
    with pytest.raises(FileNotFoundError):
        extractor.extract(tmp_path / "missing.pdf")


def test_ollama_must_be_local():
    with pytest.raises(Exception):
        OllamaVisionExtractor(host="http://example.com:11434", post=fake_post([], []))


def test_extractor_declares_it_runs_in_the_chat_gpu_group():
    assert OllamaVisionExtractor(post=fake_post([], [])).gpu_mode == "chat"
