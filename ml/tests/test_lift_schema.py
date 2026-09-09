import pytest
from ml.rag.ingest.lift_schema import CLINICAL_DOCUMENT_SCHEMA, validate_lift_payload


def test_schema_has_no_enums_or_forbidden_keywords():
    schema_str = str(CLINICAL_DOCUMENT_SCHEMA)
    assert "'enum'" not in schema_str
    assert "'anyOf'" not in schema_str
    assert "'oneOf'" not in schema_str
    assert "'$ref'" not in schema_str
    assert "'additionalProperties'" not in schema_str


def test_schema_contains_rich_descriptions():
    props = CLINICAL_DOCUMENT_SCHEMA["properties"]
    assert "description" in props["document_date"]
    assert "description" in props["observations"]["items"]["properties"]["name"]
    assert "description" in props["medications"]["items"]["properties"]["name"]
    assert "description" in props["conditions"]["items"]["properties"]["name"]
    assert "description" in props["narrative_sections"]["items"]["properties"]["content"]


def test_schema_top_level_structure():
    assert CLINICAL_DOCUMENT_SCHEMA["type"] == "object"
    assert "observations" in CLINICAL_DOCUMENT_SCHEMA["required"]
    assert "medications" in CLINICAL_DOCUMENT_SCHEMA["required"]
    assert "conditions" in CLINICAL_DOCUMENT_SCHEMA["required"]


def test_validate_lift_payload_normalizes_data():
    raw_payload = {
        "document_date": "10/03/2026",
        "document_type": "Blood Test Report",
        "observations": [
            {"name": "LDL Cholesterol", "value": "162", "unit": "mg/dL", "interpretation": "High"}
        ],
        "medications": [
            {"name": "Atorvastatin", "dosage": "20 mg", "frequency": "daily", "status": "started"}
        ],
        "conditions": [
            {"name": "Hyperlipidemia", "status": "active"}
        ],
        "narrative_sections": [
            {"heading": "Impression", "content": "Elevated lipids."}
        ],
    }
    validated = validate_lift_payload(raw_payload)
    assert validated["document_date"] == "10/03/2026"
    assert validated["document_type"] == "Blood Test Report"
    assert len(validated["observations"]) == 1
    assert validated["observations"][0]["name"] == "LDL Cholesterol"
    assert len(validated["medications"]) == 1
    assert len(validated["conditions"]) == 1
    assert len(validated["narrative_sections"]) == 1


def test_validate_lift_payload_handles_missing_optional_keys():
    empty_payload = {}
    validated = validate_lift_payload(empty_payload)
    assert validated["document_date"] is None
    assert validated["document_type"] is None
    assert validated["observations"] == []
    assert validated["medications"] == []
    assert validated["conditions"] == []
    assert validated["narrative_sections"] == []


def test_validate_lift_payload_handles_none_or_invalid_type():
    assert validate_lift_payload(None) == {
        "document_date": None,
        "document_type": None,
        "observations": [],
        "medications": [],
        "conditions": [],
        "narrative_sections": [],
    }
    assert validate_lift_payload("invalid") == {
        "document_date": None,
        "document_type": None,
        "observations": [],
        "medications": [],
        "conditions": [],
        "narrative_sections": [],
    }


def test_validate_lift_payload_filters_malformed_items():
    raw_payload = {
        "observations": [
            {"name": "HDL", "value": "50"},  # valid
            {"name": "LDL"},  # missing value
            {"value": "100"},  # missing name
            "not a dict",
        ],
        "medications": [
            {"name": "Metformin"},  # valid
            {"dosage": "500mg"},  # missing name
            123,
        ],
        "conditions": [
            {"name": "Diabetes"},  # valid
            {"status": "active"},  # missing name
            None,
        ],
        "narrative_sections": [
            {"heading": "Note", "content": "Patient reports feeling well."},  # valid
            {"heading": "Empty"},  # missing content
            [],
        ],
    }
    validated = validate_lift_payload(raw_payload)
    assert len(validated["observations"]) == 1
    assert validated["observations"][0]["name"] == "HDL"
    assert len(validated["medications"]) == 1
    assert validated["medications"][0]["name"] == "Metformin"
    assert len(validated["conditions"]) == 1
    assert validated["conditions"][0]["name"] == "Diabetes"
    assert len(validated["narrative_sections"]) == 1
    assert validated["narrative_sections"][0]["heading"] == "Note"


def test_validate_lift_payload_handles_null_array_fields():
    null_arrays_payload = {
        "document_date": None,
        "document_type": None,
        "observations": None,
        "medications": None,
        "conditions": None,
        "narrative_sections": None,
    }
    validated = validate_lift_payload(null_arrays_payload)
    assert validated["observations"] == []
    assert validated["medications"] == []
    assert validated["conditions"] == []
    assert validated["narrative_sections"] == []
