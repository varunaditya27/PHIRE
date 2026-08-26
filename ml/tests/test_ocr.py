"""
Unit tests for ml/rag/ingest/ocr.py: response parsing (extract_text_from_response)
and OCRTextExtractor's file-type routing/host enforcement. Covers all
response shapes actually observed live from different olmOCR
checkpoints/quantizations — JSON with natural_text, YAML front matter +
markdown body, and malformed JSON missing the key literal.
"""

from pathlib import Path

import pytest

from ml.rag.ingest.ocr import OCRTextExtractor, extract_text_from_response


def test_extract_text_from_json_natural_text_response():
    raw = '{"primary_language":"en","is_table":false,"natural_text":"LDL: 178 mg/dL"}'
    assert extract_text_from_response(raw) == "LDL: 178 mg/dL"


def test_extract_text_from_yaml_front_matter_response():
    raw = "---\nprimary_language: en\nis_table: false\n---\nLDL: 178 mg/dL"
    assert extract_text_from_response(raw) == "LDL: 178 mg/dL"


def test_extract_text_handles_plain_text_response():
    assert extract_text_from_response("LDL: 178 mg/dL") == "LDL: 178 mg/dL"


def test_extract_text_recovers_malformed_json_missing_key_name():
    # Observed live from olmOCR-v1 at Q4_K_M without RESPONSE_SCHEMA
    # applied: valid-looking JSON except the "natural_text" key literal
    # is missing entirely before its value.
    raw = '{"primary_language":"en","is_table":false,"LDL: 178 mg/dL\\nHDL: 41 mg/dL"}'
    assert extract_text_from_response(raw) == "LDL: 178 mg/dL\nHDL: 41 mg/dL"


def test_ocr_extractor_supports_image_formats_not_pdf():
    extractor = OCRTextExtractor()
    assert extractor.supports(Path("photo.jpg")) is True
    assert extractor.supports(Path("photo.JPEG")) is True
    assert extractor.supports(Path("photo.png")) is True
    assert extractor.supports(Path("report.pdf")) is False


def test_ocr_extractor_rejects_remote_host():
    with pytest.raises(ValueError, match="localhost"):
        OCRTextExtractor(host="http://some-remote-server.example.com:11434")
