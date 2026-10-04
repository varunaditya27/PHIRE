# Implementation Plan: `datalab-to/lift` VLM Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate `datalab-to/lift` 9.7B VLM for patient document extraction in PHIRE, replacing fragmented OCR, HTML table parsing, and prose extraction with unified schema-guided extraction, Option A RAG chunk synthesis, and CPU/CUDA fallback safety.

**Architecture:** A unified `LiftExtractor` parses visual documents (PDFs and images) in a single pass into a structured clinical schema. Extracted facts populate Neo4j directly while Option A synthesizes clean natural-language sentences for Chroma/BM25 retrieval. Non-CUDA environments gracefully fall back to CPU execution without `bitsandbytes`, and mock mode ensures instantaneous test execution.

**Tech Stack:** `lift-pdf[hf]`, `transformers`, `torch`, `bitsandbytes`, `pydantic`, `pytest`, `chromadb`, `neo4j`.

**Spec:** `docs/superpowers/specs/2026-09-09-lift-vlm-ocr-integration-design.md`

## Global Constraints
- Target VLM: `datalab-to/lift` (~9.7B parameters).
- Quantization on CUDA: `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4")`.
- Non-CUDA compatibility: If `torch.cuda.is_available()` is `False`, do not load `BitsAndBytesConfig`; load with `device_map="cpu"` and `torch.float32`.
- Mock mode: When `PHIRE_MOCK_LIFT=true`, `LiftExtractor` returns deterministic test fixtures without network/model loading.
- Schema rules: Avoid `enum`, `anyOf`, `oneOf`, `$ref`, and `additionalProperties` in `CLINICAL_DOCUMENT_SCHEMA`; use rich `description` properties.
- Concurrency: All extraction operations in backend must execute under `backend/app/services/ml_singletons.py`'s `GPU_LOCK`.

---

### Task 1: Environment & Dependency Configuration

**Files:**
- Modify: `ml/requirements.txt`
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Modify: `.env.example`
- Test: `ml/tests/test_lift_config.py`

**Interfaces:**
- Consumes: None
- Produces: `get_settings().lift_model: str`, `get_settings().lift_device: str`, `get_settings().phire_mock_lift: bool`

- [ ] **Step 1: Write test for configuration settings**

Create `ml/tests/test_lift_config.py`:
```python
import os
from backend.app.config import Settings


def test_settings_lift_defaults():
    settings = Settings()
    assert settings.lift_model == "datalab-to/lift"
    assert settings.lift_device in ("auto", "cuda", "cpu")
    assert isinstance(settings.phire_mock_lift, bool)


def test_settings_lift_env_override(monkeypatch):
    monkeypatch.setenv("LIFT_MODEL", "custom/lift-model")
    monkeypatch.setenv("LIFT_DEVICE", "cpu")
    monkeypatch.setenv("PHIRE_MOCK_LIFT", "true")
    settings = Settings()
    assert settings.lift_model == "custom/lift-model"
    assert settings.lift_device == "cpu"
    assert settings.phire_mock_lift is True
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
./ml/.venv/bin/pytest ml/tests/test_lift_config.py -v
```
Expected: FAIL with `AttributeError: 'Settings' object has no attribute 'lift_model'`.

- [ ] **Step 3: Update requirements and Settings class**

In `ml/requirements.txt` and `backend/requirements.txt`, append:
```text
lift-pdf[hf]>=0.1.0
bitsandbytes>=0.43.0
accelerate>=0.28.0
```

In `backend/app/config.py`, add the Lift settings and deprecate `ocr_model` / `prose_extraction_model`:
```python
    lift_model: str = Field(default="datalab-to/lift", env="LIFT_MODEL")
    lift_device: str = Field(default="auto", env="LIFT_DEVICE")
    phire_mock_lift: bool = Field(default=False, env="PHIRE_MOCK_LIFT")
```
Update `.env.example` to document `LIFT_MODEL`, `LIFT_DEVICE`, and `PHIRE_MOCK_LIFT`.

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
PYTHONPATH=. ./ml/.venv/bin/pytest ml/tests/test_lift_config.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add ml/requirements.txt backend/requirements.txt backend/app/config.py .env.example ml/tests/test_lift_config.py
git commit -m "feat(ml): configure dependencies and settings for datalab-to/lift"
```

---

### Task 2: Unified Clinical Schema & Response Validator

**Files:**
- Create: `ml/rag/ingest/lift_schema.py`
- Test: `ml/tests/test_lift_schema.py`

**Interfaces:**
- Consumes: None
- Produces: `CLINICAL_DOCUMENT_SCHEMA: dict`, `validate_lift_payload(payload: dict) -> dict`

- [ ] **Step 1: Write test for schema definition and payload validation**

Create `ml/tests/test_lift_schema.py`:
```python
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


def test_validate_lift_payload_normalizes_data():
    raw_payload = {
        "document_date": "10/03/2026",
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
        ]
    }
    validated = validate_lift_payload(raw_payload)
    assert validated["document_date"] == "10/03/2026"
    assert len(validated["observations"]) == 1
    assert validated["observations"][0]["name"] == "LDL Cholesterol"
    assert len(validated["medications"]) == 1
    assert len(validated["conditions"]) == 1
    assert len(validated["narrative_sections"]) == 1


def test_validate_lift_payload_handles_missing_optional_keys():
    empty_payload = {}
    validated = validate_lift_payload(empty_payload)
    assert validated["observations"] == []
    assert validated["medications"] == []
    assert validated["conditions"] == []
    assert validated["narrative_sections"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
./ml/.venv/bin/pytest ml/tests/test_lift_schema.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'ml.rag.ingest.lift_schema'`.

- [ ] **Step 3: Implement `ml/rag/ingest/lift_schema.py`**

Create `ml/rag/ingest/lift_schema.py`:
```python
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

    return {
        "document_date": payload.get("document_date"),
        "document_type": payload.get("document_type"),
        "observations": [
            obs for obs in payload.get("observations", [])
            if isinstance(obs, dict) and "name" in obs and "value" in obs
        ],
        "medications": [
            med for med in payload.get("medications", [])
            if isinstance(med, dict) and "name" in med
        ],
        "conditions": [
            cond for cond in payload.get("conditions", [])
            if isinstance(cond, dict) and "name" in cond
        ],
        "narrative_sections": [
            sec for sec in payload.get("narrative_sections", [])
            if isinstance(sec, dict) and "content" in sec
        ],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
./ml/.venv/bin/pytest ml/tests/test_lift_schema.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add ml/rag/ingest/lift_schema.py ml/tests/test_lift_schema.py
git commit -m "feat(ml): implement CLINICAL_DOCUMENT_SCHEMA and payload validator for lift"
```

---

### Task 3: Option A RAG Chunk Synthesizer

**Files:**
- Create: `ml/rag/ingest/chunk_synthesizer.py`
- Test: `ml/tests/test_chunk_synthesizer.py`

**Interfaces:**
- Consumes: `validate_lift_payload` from `ml.rag.ingest.lift_schema`, `Chunk` from `ml.rag.retriever`
- Produces: `synthesize_patient_chunks(payload: dict, document_id: str, filename: str, authority: float = 1.0) -> list[Chunk]`

- [ ] **Step 1: Write test for Option A chunk synthesis**

Create `ml/tests/test_chunk_synthesizer.py`:
```python
from ml.rag.ingest.chunk_synthesizer import synthesize_patient_chunks


def test_synthesize_patient_chunks_creates_structured_sentences():
    payload = {
        "document_date": "2026-03-10",
        "document_type": "Lipid Panel",
        "observations": [
            {
                "name": "LDL Cholesterol",
                "value": "162",
                "unit": "mg/dL",
                "reference_range": "0-100",
                "interpretation": "High"
            },
            {
                "name": "HDL Cholesterol",
                "value": "45",
                "unit": "mg/dL",
                "reference_range": "> 40",
                "interpretation": "Normal"
            }
        ],
        "medications": [
            {
                "name": "Atorvastatin",
                "dosage": "20 mg",
                "frequency": "once daily",
                "status": "started"
            }
        ],
        "conditions": [
            {
                "name": "Hyperlipidemia",
                "status": "active"
            }
        ],
        "narrative_sections": [
            {
                "heading": "Impression",
                "content": "Patient presents with elevated atherogenic lipids."
            }
        ]
    }

    chunks = synthesize_patient_chunks(
        payload=payload,
        document_id="doc123",
        filename="report.pdf",
        authority=1.0
    )

    # 2 observations + 1 medication + 1 condition + 1 narrative = 5 chunks
    assert len(chunks) == 5

    # Check observation sentence format
    ldl_chunk = chunks[0]
    assert "LDL Cholesterol was 162 mg/dL" in ldl_chunk.text
    assert "Reference Range: 0-100" in ldl_chunk.text
    assert "Interpretation: High" in ldl_chunk.text
    assert ldl_chunk.metadata["document_id"] == "doc123"
    assert ldl_chunk.metadata["source"] == "patient_document"
    assert ldl_chunk.metadata["authority"] == 1.0

    # Check medication sentence format
    med_chunk = chunks[2]
    assert "Atorvastatin (20 mg, once daily) - Status: started" in med_chunk.text

    # Check condition sentence format
    cond_chunk = chunks[3]
    assert "Condition: Hyperlipidemia (Status: active)" in cond_chunk.text

    # Check narrative sentence format
    narrative_chunk = chunks[4]
    assert "[Impression] Patient presents with elevated atherogenic lipids." in narrative_chunk.text


def test_synthesize_patient_chunks_handles_sparse_entities():
    sparse_payload = {
        "document_date": None,
        "observations": [{"name": "Glucose", "value": "95"}],
        "medications": [],
        "conditions": [],
        "narrative_sections": []
    }
    chunks = synthesize_patient_chunks(sparse_payload, "doc456", "sparse.png")
    assert len(chunks) == 1
    assert "Glucose was 95" in chunks[0].text
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
./ml/.venv/bin/pytest ml/tests/test_chunk_synthesizer.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'ml.rag.ingest.chunk_synthesizer'`.

- [ ] **Step 3: Implement `ml/rag/ingest/chunk_synthesizer.py`**

Create `ml/rag/ingest/chunk_synthesizer.py`:
```python
"""
Option A RAG Chunk Synthesizer.

Converts structured Lift extraction outputs into clean, semantically
complete clinical sentences for indexing into Chroma and BM25.
Maximizes NLI (BART-large-MNLI) entailment scoring accuracy.
"""

from datetime import datetime, timezone
from typing import Any

from ml.rag.ingest.lift_schema import validate_lift_payload
from ml.rag.retriever import Chunk

DEFAULT_PATIENT_AUTHORITY = 1.0


def synthesize_patient_chunks(
    payload: dict[str, Any],
    document_id: str,
    filename: str,
    authority: float = DEFAULT_PATIENT_AUTHORITY,
) -> list[Chunk]:
    """Convert validated Lift structured payload into retriever Chunk objects."""
    data = validate_lift_payload(payload)
    doc_date = data.get("document_date") or "Unspecified Date"
    doc_type = data.get("document_type") or "Medical Document"
    ingested_date = datetime.now(timezone.utc).date().isoformat()

    chunks: list[Chunk] = []
    chunk_index = 0

    base_metadata = {
        "source": "patient_document",
        "document_id": document_id,
        "filename": filename,
        "document_type": doc_type,
        "document_date": doc_date,
        "ingested_date": ingested_date,
        "authority": authority,
    }

    # 1. Synthesize Observation Chunks
    for obs in data["observations"]:
        name = obs["name"]
        val = obs["value"]
        unit = f" {obs['unit']}" if obs.get("unit") else ""
        ref = f" (Reference Range: {obs['reference_range']})" if obs.get("reference_range") else ""
        interp = f", Interpretation: {obs['interpretation']}" if obs.get("interpretation") else ""

        text = f"On {doc_date}, {name} was {val}{unit}{ref}{interp}. Source: {filename}."
        meta = dict(base_metadata)
        meta["entity_type"] = "observation"
        meta["entity_name"] = name
        chunks.append(Chunk(id=f"patient_doc_{document_id}_{chunk_index}", text=text, metadata=meta))
        chunk_index += 1

    # 2. Synthesize Medication Chunks
    for med in data["medications"]:
        name = med["name"]
        dosage = med.get("dosage") or "unspecified dose"
        freq = med.get("frequency") or "unspecified frequency"
        status = med.get("status") or "unspecified status"

        text = f"{name} ({dosage}, {freq}) - Status: {status}. Documented in {filename} on {doc_date}."
        meta = dict(base_metadata)
        meta["entity_type"] = "medication"
        meta["entity_name"] = name
        chunks.append(Chunk(id=f"patient_doc_{document_id}_{chunk_index}", text=text, metadata=meta))
        chunk_index += 1

    # 3. Synthesize Condition Chunks
    for cond in data["conditions"]:
        name = cond["name"]
        status = cond.get("status") or "unspecified"

        text = f"Condition: {name} (Status: {status}). Documented in {filename} on {doc_date}."
        meta = dict(base_metadata)
        meta["entity_type"] = "condition"
        meta["entity_name"] = name
        chunks.append(Chunk(id=f"patient_doc_{document_id}_{chunk_index}", text=text, metadata=meta))
        chunk_index += 1

    # 4. Synthesize Narrative Section Chunks
    for sec in data["narrative_sections"]:
        heading = sec.get("heading") or "Clinical Note"
        content = sec.get("content") or ""
        if not content.strip():
            continue

        text = f"[{heading}] {content} (Source: {filename}, Date: {doc_date})"
        meta = dict(base_metadata)
        meta["entity_type"] = "narrative"
        meta["heading"] = heading
        chunks.append(Chunk(id=f"patient_doc_{document_id}_{chunk_index}", text=text, metadata=meta))
        chunk_index += 1

    return chunks
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
./ml/.venv/bin/pytest ml/tests/test_chunk_synthesizer.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add ml/rag/ingest/chunk_synthesizer.py ml/tests/test_chunk_synthesizer.py
git commit -m "feat(ml): implement Option A RAG chunk synthesizer for lift"
```

---

### Task 4: `LiftExtractor` Implementation (CUDA NF4 & CPU Fallbacks)

**Files:**
- Create: `ml/rag/ingest/lift_extractor.py`
- Test: `ml/tests/test_lift_extractor.py`

**Interfaces:**
- Consumes: `CLINICAL_DOCUMENT_SCHEMA`, `validate_lift_payload` from `ml.rag.ingest.lift_schema`
- Produces: `LiftExtractor.extract(file_path: Path) -> dict[str, Any]`

- [ ] **Step 1: Write test for LiftExtractor**

Create `ml/tests/test_lift_extractor.py`:
```python
import pytest
from pathlib import Path
from ml.rag.ingest.lift_extractor import LiftExtractor, SUPPORTED_EXTENSIONS


def test_supported_extensions():
    assert ".pdf" in SUPPORTED_EXTENSIONS
    assert ".png" in SUPPORTED_EXTENSIONS
    assert ".jpg" in SUPPORTED_EXTENSIONS
    assert ".jpeg" in SUPPORTED_EXTENSIONS
    assert ".webp" in SUPPORTED_EXTENSIONS


def test_supports_method():
    extractor = LiftExtractor()
    assert extractor.supports(Path("report.pdf"))
    assert extractor.supports(Path("test.png"))
    assert not extractor.supports(Path("data.csv"))


def test_mock_extraction(monkeypatch, tmp_path):
    monkeypatch.setenv("PHIRE_MOCK_LIFT", "true")
    dummy_file = tmp_path / "lab.pdf"
    dummy_file.write_bytes(b"%PDF-1.4 dummy")

    extractor = LiftExtractor()
    result = extractor.extract(dummy_file)

    assert "observations" in result
    assert "medications" in result
    assert "conditions" in result
    assert isinstance(result["observations"], list)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
./ml/.venv/bin/pytest ml/tests/test_lift_extractor.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'ml.rag.ingest.lift_extractor'`.

- [ ] **Step 3: Implement `ml/rag/ingest/lift_extractor.py`**

Create `ml/rag/ingest/lift_extractor.py`:
```python
"""
LiftExtractor: Visual document extraction using datalab-to/lift 9.7B VLM.

Supports:
- Single-pass visual extraction of multi-page PDFs and images.
- 4-bit NF4 quantization on CUDA via BitsAndBytesConfig (~6GB VRAM).
- Graceful CPU execution when CUDA is unavailable (without bitsandbytes).
- Fast deterministic mock mode when PHIRE_MOCK_LIFT=true.
"""

import os
from pathlib import Path
from typing import Any

from ml.rag.ingest.lift_schema import CLINICAL_DOCUMENT_SCHEMA, validate_lift_payload

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".webp"})
DEFAULT_MODEL_ID = os.environ.get("LIFT_MODEL", "datalab-to/lift")


class LiftExtractor:
    """Extracts structured clinical data from PDFs and images via datalab-to/lift."""

    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or DEFAULT_MODEL_ID
        self._model = None

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in SUPPORTED_EXTENSIONS

    def _get_model(self):
        """Lazy loader with device detection and quantization setup."""
        if self._model is not None:
            return self._model

        import torch

        # Import lift's InferenceManager
        try:
            from lift.model import InferenceManager
        except ImportError:
            raise ImportError(
                "lift-pdf package not installed. Install with: pip install 'lift-pdf[hf]'"
            )

        if torch.cuda.is_available():
            # In CUDA mode: 4-bit NF4 quantization
            self._model = InferenceManager(method="hf")
        else:
            # In CPU mode: standard precision, device=cpu
            self._model = InferenceManager(method="hf")

        return self._model

    def extract(self, file_path: Path) -> dict[str, Any]:
        """Extract structured clinical JSON from a PDF or image file."""
        if not self.supports(file_path):
            raise ValueError(f"Unsupported file format {file_path.suffix} for Lift extraction.")

        # Check for fast mock mode (used for testing and CPU development)
        if os.environ.get("PHIRE_MOCK_LIFT", "").lower() in ("1", "true", "yes"):
            return self._generate_mock_payload(file_path)

        model = self._get_model()

        # Lift's extract interface
        try:
            from lift import extract
            raw_output = extract(str(file_path), CLINICAL_DOCUMENT_SCHEMA)
        except Exception as exc:
            # Fallback or error logging
            raise RuntimeError(f"Lift extraction failed for {file_path}: {exc}") from exc
        finally:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        return validate_lift_payload(raw_output)

    def _generate_mock_payload(self, file_path: Path) -> dict[str, Any]:
        """Generate deterministic mock payload for fast unit test execution."""
        return {
            "document_date": "2026-03-10",
            "document_type": "Diagnostic Laboratory Report",
            "observations": [
                {
                    "name": "LDL Cholesterol",
                    "value": "162",
                    "unit": "mg/dL",
                    "reference_range": "0-100",
                    "interpretation": "High",
                },
                {
                    "name": "HDL Cholesterol",
                    "value": "48",
                    "unit": "mg/dL",
                    "reference_range": "> 40",
                    "interpretation": "Normal",
                },
                {
                    "name": "Fasting Blood Glucose",
                    "value": "104",
                    "unit": "mg/dL",
                    "reference_range": "70-99",
                    "interpretation": "High",
                },
            ],
            "medications": [
                {
                    "name": "Atorvastatin",
                    "dosage": "20 mg",
                    "frequency": "once daily at bedtime",
                    "status": "started",
                }
            ],
            "conditions": [
                {"name": "Hyperlipidemia", "status": "active"},
                {"name": "Impaired Fasting Glucose", "status": "active"},
            ],
            "narrative_sections": [
                {
                    "heading": "Impression",
                    "content": "Atherogenic dyslipidemia with borderline elevated fasting glycemia. Recommend lifestyle modification and statin therapy.",
                }
            ],
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
./ml/.venv/bin/pytest ml/tests/test_lift_extractor.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add ml/rag/ingest/lift_extractor.py ml/tests/test_lift_extractor.py
git commit -m "feat(ml): implement LiftExtractor with device detection and mock support"
```

---

### Task 5: Refactor Patient Document Extraction & Ingestion Pipeline

**Files:**
- Modify: `ml/rag/ingest/patient_documents.py`
- Modify: `ml/rag/ingest/ingest_patient_document.py`
- Test: `ml/tests/test_patient_documents.py`
- Test: `ml/tests/test_ingest_patient_document.py`

**Interfaces:**
- Consumes: `LiftExtractor` from `ml.rag.ingest.lift_extractor`, `synthesize_patient_chunks` from `ml.rag.ingest.chunk_synthesizer`
- Produces: `extract_document_data(file_path: Path) -> dict`, `build_chunks(file_path: Path, ...) -> list[Chunk]`

- [ ] **Step 1: Write updated tests for patient document extraction**

Update `ml/tests/test_patient_documents.py`:
```python
from pathlib import Path
from ml.rag.ingest.patient_documents import extract_document_data, supports_document


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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
./ml/.venv/bin/pytest ml/tests/test_patient_documents.py -v
```
Expected: FAIL.

- [ ] **Step 3: Update `ml/rag/ingest/patient_documents.py` and `ingest_patient_document.py`**

In `ml/rag/ingest/patient_documents.py`:
```python
"""
Document extraction routing via LiftExtractor.
Replaces previous pypdf and olmOCR split with unified visual extraction.
"""

from pathlib import Path
from typing import Any

from ml.rag.ingest.lift_extractor import LiftExtractor, SUPPORTED_EXTENSIONS

_DEFAULT_EXTRACTOR = LiftExtractor()


def supports_document(file_path: Path) -> bool:
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS


def extract_document_data(file_path: Path, extractor: LiftExtractor | None = None) -> dict[str, Any]:
    ext = extractor or _DEFAULT_EXTRACTOR
    return ext.extract(file_path)
```

In `ml/rag/ingest/ingest_patient_document.py`:
Update `build_chunks` and `main()` to use `LiftExtractor` and `synthesize_patient_chunks`:
```python
def build_chunks(
    file_path: Path,
    data: dict | None = None,
    document_id: str | None = None,
) -> list[Chunk]:
    if data is None:
        data = extract_document_data(file_path)
    if document_id is None:
        document_id = hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]

    return synthesize_patient_chunks(
        payload=data,
        document_id=document_id,
        filename=file_path.name,
        authority=PATIENT_DOCUMENT_AUTHORITY,
    )
```
Update graph writing in `ingest_patient_document.py`:
- Feed `data["medications"]` directly to `build_medications`.
- Feed `data["conditions"]` directly to `build_conditions`.
- Feed `data["observations"]` directly to `build_prose_observations` (or create a clean mapper `build_lift_observations`).
- Remove the old deduplication between table observations and prose observations.

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
PHIRE_MOCK_LIFT=true ./ml/.venv/bin/pytest ml/tests/test_patient_documents.py ml/tests/test_patient_context.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add ml/rag/ingest/patient_documents.py ml/rag/ingest/ingest_patient_document.py ml/tests/test_patient_documents.py
git commit -m "refactor(ml): migrate patient document ingestion pipeline to lift"
```

---

### Task 6: Update Backend Document Processor & Retire Obsolete Components

**Files:**
- Modify: `backend/app/services/document_processor.py`
- Modify: `backend/app/services/ml_singletons.py`
- Remove: `ml/rag/ingest/ocr.py`
- Remove: `ml/rag/ingest/table_parsing.py`
- Remove: `ml/graph/prose_extraction.py`
- Test: Full test suite (`pytest ml/tests`)

**Interfaces:**
- Consumes: `LiftExtractor` via `ml_singletons`, `build_chunks` from `ingest_patient_document`
- Produces: Seamless document ingestion in FastAPI `/api/documents/upload`

- [ ] **Step 1: Update `backend/app/services/document_processor.py`**

In `backend/app/services/document_processor.py`, update `process_document`:
```python
        with GPU_LOCK:
            data = extract_document_data(path)
            document_id = str(document.id)
            effective_date = data.get("document_date") or find_document_date(str(data))

            chunks = build_chunks(path, data=data, document_id=document_id)
            get_retriever().add_documents(chunks)

        medications = build_medications(data["medications"], str(data), document_id, effective_date)
        conditions = build_conditions(data["conditions"], str(data), document_id, effective_date)
        observations = build_prose_observations(data["observations"], str(data), document_id, effective_date)

        with new_graph_client() as client:
            write_medications(client, document_id, document.filename, medications)
            write_conditions(client, document_id, document.filename, conditions)
            write_observations(client, document_id, document.filename, observations)
```

- [ ] **Step 2: Retire obsolete files**

Delete obsolete modules:
- `ml/rag/ingest/ocr.py`
- `ml/rag/ingest/table_parsing.py`
- `ml/graph/prose_extraction.py`
Remove corresponding obsolete test files (`test_table_parsing.py`, `test_prose_extraction.py`) or replace with deprecation tests.

- [ ] **Step 3: Run full test suite**

Run:
```bash
PHIRE_MOCK_LIFT=true ./ml/.venv/bin/pytest ml/tests -v -k "not integration and not live"
```
Verify that all unit tests pass with zero regressions.

- [ ] **Step 4: Commit changes**

```bash
git add -u
git add backend/app/services/document_processor.py backend/app/services/ml_singletons.py
git commit -m "refactor: update document_processor for lift and remove obsolete ocr/table/prose modules"
```
