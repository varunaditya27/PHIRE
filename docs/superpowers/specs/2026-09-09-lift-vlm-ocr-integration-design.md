# Design Specification: End-to-End Document Extraction with `datalab-to/lift` VLM

**Document**: `docs/superpowers/specs/2026-09-09-lift-vlm-ocr-integration-design.md`  
**Date**: September 9, 2026  
**Status**: Pending Review  
**Subsystem**: `ml/rag/ingest`, `ml/graph`, `backend/app/services`

---

## 1. Executive Summary & Motivation

### Current Problem
PHIRE's patient document ingestion currently relies on a fragmented, multi-stage pipeline:
1. `PDFTextExtractor` uses `pypdf` for digital PDFs (which fails silently or outputs empty text on scanned/image-only PDFs).
2. `OCRTextExtractor` calls a local vision model (`olmOCR-2-7B` via Ollama) only for raw image files (`.png`, `.jpg`).
3. Extracted markdown is split into two ad-hoc extraction paths:
   - `table_parsing.py` regex-searches for `<table>` HTML tags emitted by olmOCR.
   - `prose_extraction.py` invokes `qwen3.5:9b` via Ollama with `EXTRACTION_SCHEMA`.
4. Extracted observations from both paths must be deduplicated with arbitrary tie-breaking heuristics.
5. VRAM contention is severe on 8GB GPUs: Ollama olmOCR, Ollama Qwen 9B, and in-process MedCPT embeddings compete for memory, requiring aggressive `keep_alive: 0` unloads and sequential locking.

### Proposed Solution
Replace the entire multi-stage OCR, table parsing, and prose extraction cascade with **`datalab-to/lift`** (a ~9.7B parameter vision-language model developed by Datalab).

`datalab-to/lift` performs **schema-guided visual extraction directly from rendered pages of PDFs and image documents** in a single pass. It unifies:
- Document date extraction
- Structured lab observations & vital signs (from tables or text)
- Medications (dosage, frequency, status)
- Clinical conditions / diagnoses
- Narrative clinical notes & impressions

---

## 2. Architecture & Execution Strategy

### 2.1 Model Specifications & Execution Strategy
- **Hugging Face Checkpoint**: `datalab-to/lift` (~9.7B parameters, vision-to-json).
- **Primary Package**: `lift-pdf[hf]` with `transformers`, `torch`, `bitsandbytes`, and `accelerate`.
- **Quantization on CUDA**:
  - Automatically enabled when `torch.cuda.is_available()`.
  - Configured with `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4")`.
  - Peak VRAM footprint: **~6.0–6.5 GB**, fitting comfortably on 8GB consumer GPUs (RTX 3060/3070/4060).
- **CPU & Non-CUDA Laptop Compatibility**:
  - If CUDA is not detected (`torch.cuda.is_available() is False`), the system automatically disables `BitsAndBytesConfig` (avoiding the fatal `ValueError: 4-bit quantization only supported on CUDA GPUs`).
  - Model loads with `torch.float32` (or `torch.bfloat16` where supported) with `device_map="cpu"`.
  - For resource-constrained test environments, an environment variable `PHIRE_MOCK_LIFT=true` will provide a deterministic fallback extractor so automated unit tests run instantaneously on any machine without downloading 10GB weights.

### 2.2 Memory Management & `GPU_LOCK`
- All Lift extractions run under `backend/app/services/ml_singletons.py`'s `GPU_LOCK`.
- The `LiftExtractor` is instantiated as a lazy singleton.
- After processing a document batch, explicit memory cleanup is executed:
  ```python
  if torch.cuda.is_available():
      torch.cuda.empty_cache()
  ```

---

## 3. Unified Clinical JSON Schema

In accordance with official Datalab Lift best practices:
- Rich, highly descriptive `description` fields guide the visual token attention.
- Complex grammar constraints like `enum`, `anyOf`, `oneOf`, `$ref`, and `additionalProperties` are omitted to ensure reliable grammar compilation during schema-constrained decoding. Categorical values are validated in Python post-extraction.

```json
{
  "type": "object",
  "properties": {
    "document_date": {
      "type": "string",
      "description": "Date of the medical report, lab test, encounter, or specimen collection in DD/MM/YYYY or YYYY-MM-DD format"
    },
    "document_type": {
      "type": "string",
      "description": "Category of medical document, such as Blood Test Report, Lipid Panel, Discharge Summary, Radiology Report, or Prescription"
    },
    "observations": {
      "type": "array",
      "description": "All clinical measurements, laboratory test results, vital signs, or panel values found in tables or text",
      "items": {
        "type": "object",
        "properties": {
          "name": { 
            "type": "string", 
            "description": "Canonical name of the analyte or test, e.g., 'LDL Cholesterol', 'Hemoglobin A1c', 'Systolic Blood Pressure'" 
          },
          "value": { 
            "type": "string", 
            "description": "Observed quantitative or qualitative result, e.g., '162', 'Positive', '5.7'" 
          },
          "unit": { 
            "type": "string", 
            "description": "Measurement unit, e.g., 'mg/dL', '%', 'mmHg', or null if unitless" 
          },
          "reference_range": { 
            "type": "string", 
            "description": "Normal or biological reference interval printed on the report, e.g., '0 - 100', '< 200'" 
          },
          "interpretation": { 
            "type": "string", 
            "description": "Clinical flag or status indicator: normal, high, low, critical, or abnormal" 
          }
        },
        "required": ["name", "value"]
      }
    },
    "medications": {
      "type": "array",
      "description": "All prescription drugs, over-the-counter medications, or supplements listed in the document",
      "items": {
        "type": "object",
        "properties": {
          "name": { 
            "type": "string", 
            "description": "Generic or brand name of the drug, e.g., 'Atorvastatin', 'Metformin'" 
          },
          "dosage": { 
            "type": "string", 
            "description": "Strength or dose amount, e.g., '20 mg', '500 mg'" 
          },
          "frequency": { 
            "type": "string", 
            "description": "Administration schedule, e.g., 'once daily at bedtime', 'BID with meals'" 
          },
          "status": { 
            "type": "string", 
            "description": "Current status of this medication: started, continued, discontinued, or unspecified" 
          }
        },
        "required": ["name"]
      }
    },
    "conditions": {
      "type": "array",
      "description": "All diagnoses, past medical history items, symptoms, or active medical conditions",
      "items": {
        "type": "object",
        "properties": {
          "name": { 
            "type": "string", 
            "description": "Medical condition or diagnosis name, e.g., 'Type 2 Diabetes Mellitus', 'Hyperlipidemia'" 
          },
          "status": { 
            "type": "string", 
            "description": "Clinical status: active, resolved, historical, or unspecified" 
          }
        },
        "required": ["name"]
      }
    },
    "narrative_sections": {
      "type": "array",
      "description": "Key textual sections, doctor's impressions, clinical notes, or summary remarks",
      "items": {
        "type": "object",
        "properties": {
          "heading": { 
            "type": "string", 
            "description": "Title or category of the section, e.g., 'Impression', 'Clinical History', 'Recommendations'" 
          },
          "content": { 
            "type": "string", 
            "description": "Complete text or notes transcribed from that section" 
          }
        },
        "required": ["heading", "content"]
      }
    }
  },
  "required": ["observations", "medications", "conditions"]
}
```

---

## 4. End-to-End Pipeline & Option A RAG Chunking

### 4.1 Ingestion Flow
1. **File Input**: Accepts PDF (text or scanned) or Image (`.png`, `.jpg`, `.jpeg`, `.webp`).
2. **Extraction**: `LiftExtractor.extract(file_path)` invokes `lift` with `CLINICAL_DOCUMENT_SCHEMA`, returning the structured JSON dict.
3. **Date Resolution**:
   - Primary: Uses `document_date` returned by Lift.
   - Fallback: Validates via `ml.graph.document_dates.find_document_date()`.
4. **Graph Persistence (Neo4j)**:
   - `build_observations()` maps Lift observations directly to `:Observation` nodes.
   - `build_medications()` maps Lift medications directly to `:Medication` nodes.
   - `build_conditions()` maps Lift conditions directly to `:Condition` nodes.
   - All nodes link to `(:Document {id, filename})` via `[:FROM_DOCUMENT]`.
5. **RAG Chunk Synthesis (Option A)**:
   - Instead of indexing brittle OCR text fragments, the structured data is converted into clean, semantically complete clinical sentences:
     * **Observations**: `"On {date}, {name} was {value} {unit} (Reference Range: {reference_range}, Interpretation: {interpretation}). Source: {filename}."`
     * **Medications**: `"{name} ({dosage}, {frequency}) - Status: {status}. Documented in {filename} on {date}."`
     * **Conditions**: `"Condition: {name} (Status: {status}). Documented in {filename} on {date}."`
     * **Narrative Sections**: `"[{heading}] {content} (Source: {filename}, Date: {date})"`
   - Chunks are wrapped in `Chunk(id=..., text=..., metadata={"source": "patient_document", "document_id": ...})` and indexed into Chroma (`phire_evidence`) and `BM25Okapi`.
   - **Advantage for NLI Verifier**: Natural language sentence formats maximize `BART-large-MNLI` entailment scoring accuracy and eliminate formatting false-contradictions.

---

## 5. Components to Retire & Clean Up

| Component | Path | Action |
|---|---|---|
| `OCRTextExtractor` | `ml/rag/ingest/ocr.py` | **Delete** file or replace with deprecation stub |
| `_TableRowParser` | `ml/rag/ingest/table_parsing.py` | **Delete** file or retire |
| `extract_facts` (qwen) | `ml/graph/prose_extraction.py` | **Retire / Replace** with Lift extraction |
| `PDFTextExtractor` | `ml/rag/ingest/patient_documents.py` | **Refactor** to delegate all formats to `LiftExtractor` |
| Ollama OCR / Qwen configs | `backend/app/config.py`, `.env.example` | Remove `OCR_MODEL` and `PROSE_EXTRACTION_MODEL` dependencies |

---

## 6. Testing & Validation Plan

1. **Unit Tests**:
   - `ml/tests/test_lift_extractor.py`: Test extraction output parsing, schema conformity, and CPU/CUDA fallback flags.
   - Test Option A chunk synthesis: verify that generated sentences contain all observation values, units, and citation metadata.
   - Test Graph entity mapping: ensure `write_observations`, `write_medications`, and `write_conditions` receive clean payloads.
2. **Integration Tests**:
   - End-to-end ingestion test using `ml/tests/fixtures/sample_lab_report.pdf`.
   - Verification that extracted facts appear in `HybridRetriever.retrieve()` and are verifiable by `ClaimVerifier.verify()`.
3. **Non-CUDA Test**:
   - Verify that test suite passes on CPU with `torch.cuda.is_available() == False` and `PHIRE_MOCK_LIFT=true`.

---

## 7. Migration & Rollout Steps

1. Install `lift-pdf[hf]` and dependencies in `ml/requirements.txt` and `backend/requirements.txt`.
2. Implement `ml/rag/ingest/lift_extractor.py` with schema and CPU/CUDA device management.
3. Update `ml/rag/ingest/patient_documents.py` to route all documents to `LiftExtractor`.
4. Update `ml/rag/ingest/ingest_patient_document.py` and `backend/app/services/document_processor.py`.
5. Remove obsolete modules (`ocr.py`, `table_parsing.py`, `prose_extraction.py`).
6. Run `pytest ml/tests/` to verify zero regressions.
