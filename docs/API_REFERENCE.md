# PHIRE API Reference

Generated from the actual routers/Pydantic models on `backend/` as of this
doc's last update. For live, interactive testing and schemas, run the backend and visit
`http://localhost:8000/docs` (FastAPI Swagger UI) directly.

**Base URL**: `http://localhost:8000` (Docker or local run — see
[backend/README.md](../backend/README.md)'s Quick Start). No path prefix
beyond `/api`.

**Auth**: None. PHIRE runs single-user, local-only — no login, no tokens,
no `patient_id` anywhere (see `backend/app/database/schemas.py`'s module
docstring). Every request to clinical endpoints is audited server-side regardless
(`app/security.py`'s `AuditMiddleware`).

**Errors**: Standard FastAPI/Pydantic format: `{"detail": "..."}` for a
plain error message or `{"detail": [...]}` for a 422 validation error. Status
codes used: `404` (not found), `409` (document already processing), `413`
(upload too large), `415` (unsupported file type), `422` (validation), `501`
(recommendation model not implemented yet), `502` (ML pipeline execution error).

**Content type**: `application/json` for every request/response except
`POST /api/documents/upload`, which is `multipart/form-data`.

---

## 1. Health

### `POST /api/health`
Liveness and dependency readiness check — verifies PostgreSQL, Ollama `/api/tags`, Chroma `PersistentClient.heartbeat()`, and Neo4j `RETURN 1`. Enforces local-only host verification before outbound network checks.

**Response** `HealthStatus`
```json
{
  "status": "ok",                 // "ok" | "degraded"
  "database": true,
  "ollama": true,
  "vector_store": true,
  "graph": true,
  "detail": {}                    // per-check error message, only for false values
}
```

### `GET /api/ping`
Fast liveness probe with zero dependency checks.
```json
{ "status": "ok" }
```

---

## 2. Chat

### `POST /api/chat`
The core Q&A endpoint: retrieval → cross-encoder rerank → LLM answer generation (`medgemma:4b`) → atomic claim extraction (`qwen3.5:9b`) → NLI verification (`facebook/bart-large-mnli`) → confidence scoring → claim filtering and abstention. Executes under `GPU_LOCK`. Single blocking call, **no streaming**.

**Request** `ChatRequest`
```json
{ "message": "What was my most recent LDL cholesterol level?" }
```

**Response** `ChatResponse`
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "answer": "Your most recent LDL cholesterol level was 162 mg/dL.",
  "claims": [
    {
      "id": null,
      "statement": "Your most recent LDL cholesterol level was 162 mg/dL.",
      "status": "DERIVED",
      "confidence": 0.866,
      "source_url": null,
      "source_filename": "lab_report_2026.pdf",
      "source_span": [120, 245]
    }
  ],
  "citations": [],
  "created_at": "2026-09-03T12:00:00Z"
}
```
- `claims[].status` is one of `SUPPORTED`, `DERIVED`, `INFERRED`, `UNCERTAIN`, `CONFLICTING`, `UNSUPPORTED`.
  - `DERIVED`: Claim matched a precomputed trend fact from the Longitudinal Health Graph.
  - `SUPPORTED`: Claim was entailed by a retrieved document chunk or knowledge base passage.
  - `CONFLICTING`: Claim contradicted retrieved evidence.
  - `UNSUPPORTED`: Claim had no supporting evidence or confidence below `ABSTENTION_THRESHOLD` (0.4).
- `claims[].source_span` is serialized as a two-element integer array `[start_char_offset, end_char_offset]` (or `null`).
- **The answer text is pre-filtered**: only claims passing confidence thresholds are assembled into the returned `answer`.

*(Note: `GET /api/chat/messages` for loading chat history on page load is tracked on the backlog).*

---

## 3. Documents

### `POST /api/documents/upload`
Accepts `multipart/form-data` with field `file` (PDF, PNG, JPEG). Streams upload with a 25MB safety cap (`UPLOAD_MAX_SIZE_BYTES`), saves original artifact to disk as `{uuid4}.{ext}`, writes row to PostgreSQL `documents` table, and queues background ML ingestion.

**Response** `DocumentUploadResponse`
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "filename": "lab_report.pdf",
  "status": "uploaded"
}
```

### `POST /api/documents/{document_id}/process`
Re-triggers background ingestion for an existing document. Uses an atomic SQL conditional update to guard against race conditions.
- Returns `404` if document not found.
- Returns `409` if document status is already `processing`.

### `GET /api/documents/{document_id}`
Queries document status and processing metadata.
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "filename": "lab_report.pdf",
  "content_type": "application/pdf",
  "status": "processed",             // "uploaded" | "processing" | "processed" | "failed"
  "uploaded_at": "2026-09-03T12:00:00Z",
  "processed_at": "2026-09-03T12:00:15Z",
  "error_message": null
}
```

*(Note: `GET /api/documents` to list all uploaded documents in PostgreSQL is tracked on the backlog).*

---

## 4. Observations & Timeline

All observations and timeline series read live from the Neo4j Longitudinal Health Graph (single-patient `DEFAULT_PATIENT_ID = "self"`).

### `GET /api/observations`
Query parameters (optional):
- `type`: `lab` | `medication` | `condition` | `symptom` | `vital`
- `start_date`: ISO format (`YYYY-MM-DD`)
- `end_date`: ISO format (`YYYY-MM-DD`)

**Response** `list[ObservationRead]`
```json
[
  {
    "id": "obs_patient_doc_123_0",
    "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "type": "lab",
    "name": "LDL Cholesterol",
    "value": "162",
    "value_numeric": 162.0,
    "unit": "mg/dL",
    "reference_range": "0-100",
    "interpretation": "high",
    "status": null,
    "observed_date": "2026-08-20"
  }
]
```

### `GET /api/timeline`
Builds chronological time-series points grouped by observation name for all numeric lab metrics.

**Response** `TimelineResponse`
```json
{
  "series": [
    {
      "name": "LDL Cholesterol",
      "type": "lab",
      "points": [
        {
          "observed_date": "2025-08-01",
          "value_numeric": 140.0,
          "value": "140",
          "unit": "mg/dL",
          "observation_id": "obs_1"
        },
        {
          "observed_date": "2026-08-20",
          "value_numeric": 162.0,
          "value": "162",
          "unit": "mg/dL",
          "observation_id": "obs_2"
        }
      ]
    }
  ],
  "generated_at": "2026-09-03T12:00:00Z"
}
```

---

## 5. Evidence & Claims

### `GET /api/search/evidence?query=...&top_k=5`
Executes hybrid BM25 + dense vector search via MedCPT embeddings in Chroma, fused with Reciprocal Rank Fusion ($k=60$).

**Response** `list[EvidenceCitation]`
```json
[
  {
    "evidence_passage_id": "patient_doc_123_0",
    "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "text": "Fasting Lipid Profile: Total Cholesterol 220 mg/dL, LDL Cholesterol 162 mg/dL, HDL 45 mg/dL.",
    "source_url": null,
    "source_filename": "lab_report.pdf",
    "authority": 1.0,
    "page_number": null,
    "score": 0.88
  }
]
```

### `POST /api/evidence/retrieve`
Request-body equivalent of the search endpoint: `{"query": "...", "top_k": 5}` → `{"citations": [...]}`.

### `POST /api/evidence/verify`
Retrieves candidate evidence for a standalone claim string and executes BART-large-MNLI NLI verification under `GPU_LOCK`.

**Request**: `{"claim": "Patient was prescribed Metformin 500mg daily."}`  
**Response**: `{"claim": { ...Claim shape... }}`

### `POST /api/claims/extract`
Standalone atomic claim extraction using `qwen3.5:9b`. Returns claims with status `UNCERTAIN` and `confidence: null` (extraction only, no verification).

**Request**: `{"text": "Patient has hypertension and elevated LDL."}`  
**Response**: `{"claims": [ { "statement": "Patient has hypertension.", "status": "UNCERTAIN", ... } ]}`

---

## 6. Recommendations

### `GET /api/recommendations/fitness`
### `GET /api/recommendations/nutrition`
Both endpoints currently return **`501 Not Implemented`** (`detail: "ml.recommendations.* not implemented yet"`) while recommendation ML models are under development.
