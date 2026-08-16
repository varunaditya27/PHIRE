"""
Unit test for ml/rag/ingest/experiments/candidates.py's response parsing.
Covers both response shapes actually observed from different olmOCR
checkpoints/quantizations — JSON with natural_text, and YAML front matter
+ markdown body.
"""

from ml.rag.ingest.experiments.candidates import _extract_text


def test_extract_text_from_json_natural_text_response():
    raw = '{"primary_language":"en","is_table":false,"natural_text":"LDL: 178 mg/dL"}'
    assert _extract_text(raw) == "LDL: 178 mg/dL"


def test_extract_text_from_yaml_front_matter_response():
    raw = "---\nprimary_language: en\nis_table: false\n---\nLDL: 178 mg/dL"
    assert _extract_text(raw) == "LDL: 178 mg/dL"


def test_extract_text_handles_plain_text_response():
    assert _extract_text("LDL: 178 mg/dL") == "LDL: 178 mg/dL"


def test_extract_text_recovers_malformed_json_missing_key_name():
    # Observed live from olmOCR-v1 at Q4_K_M: valid-looking JSON except the
    # "natural_text" key literal is missing entirely before its value.
    raw = '{"primary_language":"en","is_table":false,"LDL: 178 mg/dL\\nHDL: 41 mg/dL"}'
    assert _extract_text(raw) == "LDL: 178 mg/dL\nHDL: 41 mg/dL"
