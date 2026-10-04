"""
Unified clinical extraction JSON schema for datalab-to/lift VLM.

Follows official Datalab best practices:
- Uses rich field descriptions to guide attention.
- Strictly avoids enum, anyOf, oneOf, $ref, and additionalProperties to
  prevent grammar compiler failures during schema-constrained decoding.
"""

from typing import Any

CLINICAL_DOCUMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "document_date": {
            "type": "string",
            "description": "Date of the medical report, lab test, encounter, or specimen collection in DD/MM/YYYY or YYYY-MM-DD format",
        },
        "document_type": {
            "type": "string",
            "description": "Category of medical document, such as Blood Test Report, Lipid Panel, Discharge Summary, Radiology Report, or Prescription",
        },
        "observations": {
            "type": "array",
            "description": "All clinical measurements, laboratory test results, vital signs, or panel values found in tables or text",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Canonical name of the analyte or test, e.g., 'LDL Cholesterol', 'Hemoglobin A1c', 'Systolic Blood Pressure'",
                    },
                    "value": {
                        "type": "string",
                        "description": "Observed quantitative or qualitative result, e.g., '162', 'Positive', '5.7'",
                    },
                    "unit": {
                        "type": "string",
                        "description": "Measurement unit, e.g., 'mg/dL', '%', 'mmHg', or null if unitless",
                    },
                    "reference_range": {
                        "type": "string",
                        "description": "Normal or biological reference interval printed on the report, e.g., '0 - 100', '< 200'",
                    },
                    "interpretation": {
                        "type": "string",
                        "description": "Clinical flag or status indicator: normal, high, low, critical, or abnormal",
                    },
                },
                "required": ["name", "value"],
            },
        },
        "medications": {
            "type": "array",
            "description": "All prescription drugs, over-the-counter medications, or supplements listed in the document",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Generic or brand name of the drug, e.g., 'Atorvastatin', 'Metformin'",
                    },
                    "dosage": {
                        "type": "string",
                        "description": "Strength or dose amount, e.g., '20 mg', '500 mg'",
                    },
                    "frequency": {
                        "type": "string",
                        "description": "Administration schedule, e.g., 'once daily at bedtime', 'BID with meals'",
                    },
                    "status": {
                        "type": "string",
                        "description": "Current status of this medication: started, continued, discontinued, or unspecified",
                    },
                },
                "required": ["name"],
            },
        },
        "conditions": {
            "type": "array",
            "description": "All diagnoses, past medical history items, symptoms, or active medical conditions",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Medical condition or diagnosis name, e.g., 'Type 2 Diabetes Mellitus', 'Hyperlipidemia'",
                    },
                    "status": {
                        "type": "string",
                        "description": "Clinical status: active, resolved, historical, or unspecified",
                    },
                },
                "required": ["name"],
            },
        },
        "narrative_sections": {
            "type": "array",
            "description": "Key textual sections, doctor's impressions, clinical notes, or summary remarks",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {
                        "type": "string",
                        "description": "Title or category of the section, e.g., 'Impression', 'Clinical History', 'Recommendations'",
                    },
                    "content": {
                        "type": "string",
                        "description": "Complete text or notes transcribed from that section",
                    },
                },
                "required": ["heading", "content"],
            },
        },
    },
    "required": ["observations", "medications", "conditions"],
}


def validate_lift_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Validate and normalize raw Lift extraction dictionary into expected clinical structure."""
    if not isinstance(payload, dict):
        return {
            "document_date": None,
            "document_type": None,
            "observations": [],
            "medications": [],
            "conditions": [],
            "narrative_sections": [],
        }

    raw_obs = payload.get("observations")
    obs_list = raw_obs if isinstance(raw_obs, list) else []

    raw_meds = payload.get("medications")
    med_list = raw_meds if isinstance(raw_meds, list) else []

    raw_conds = payload.get("conditions")
    cond_list = raw_conds if isinstance(raw_conds, list) else []

    raw_secs = payload.get("narrative_sections")
    sec_list = raw_secs if isinstance(raw_secs, list) else []

    return {
        "document_date": payload.get("document_date"),
        "document_type": payload.get("document_type"),
        "observations": [
            obs for obs in obs_list
            if isinstance(obs, dict) and obs.get("name") is not None and obs.get("value") is not None
        ],
        "medications": [
            med for med in med_list
            if isinstance(med, dict) and med.get("name") is not None
        ],
        "conditions": [
            cond for cond in cond_list
            if isinstance(cond, dict) and cond.get("name") is not None
        ],
        "narrative_sections": [
            sec for sec in sec_list
            if isinstance(sec, dict) and sec.get("content") is not None
        ],
    }
