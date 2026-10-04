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
codes used: `404` (not found), `409` (document already processing — only from `/process`), `413`
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
The core Q&A endpoint: retrieval → cross-encoder rerank → LLM answer generation (`medgemma:4b`) → atomic claim extraction (the same local model, `medgemma:4b`) → NLI verification (`facebook/bart-large-mnli`) → confidence scoring → claim filtering and abstention. Runs inside `gpu_mode(CHAT)` (see [BACKEND_HANDOFF.md](BACKEND_HANDOFF.md)). Single blocking JSON call; use `POST /api/chat/stream` below when the caller wants live progress.

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
      "source_filenames": ["lab_report_2026.pdf"],
      "source_span": [120, 245]
    }
  ],
  "citations": [
    { "evidence_passage_id": "...", "text": "...", "source_filename": "lab_report.pdf", "source_url": null, "authority": 1.0, "score": null }
  ],
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

### `POST /api/chat/stream` (SSE)
The same turn as `POST /api/chat` (same request body, same persistence to `chat_messages` / `claims`), delivered as **Server-Sent Events** so a UI can show what the otherwise-silent pipeline is doing. `Content-Type: text/event-stream`. Because it is a POST, consume it with `fetch` + a stream reader (the browser `EventSource` is GET-only) — `frontend/lib/sse.ts` does this.

Events, in order:

| `event:` | `data:` (JSON) | Meaning |
|---|---|---|
| `progress` | `{"stage": "...", "message": "..."}` | One per pipeline stage, as it starts |
| `result` | the full `ChatResponse` (same shape as above) | Terminal — the answer |
| `error` | `{"message": "..."}` | Terminal — pipeline failed (the non-stream endpoint returns `502` instead; the assistant error turn is still persisted) |

Stages: `start` (question received), `gpu_wait` (another GPU task holds the lock), `gpu` (loading the chat-group models onto the GPU — only when the GPU was last used by lift, or on the very first request after startup), `graph` (reading the patient's graph facts), `retrieve`, `generate` (local LLM draft), `extract` (claim splitting), `verify` (one event per claim: "Verifying claim i of n"). `gpu_wait`/`gpu` appear only when applicable.

```
event: progress
data: {"stage": "generate", "message": "Drafting an answer with the local model"}

event: result
data: {"id": "...", "answer": "...", "claims": [...], "citations": [], "created_at": "..."}
```

`citations` are the reranked passages the answer was drafted from (patient-document chunks and public reference pages, `score` is `null` here — only the search endpoints compute it). Every claim carries **`source_filenames`**: all uploaded documents it rests on. A `DERIVED` trend claim lists the documents of *both* readings (e.g. `["march.pdf", "sept.png"]`); `source_filename` is the first of them, kept for older clients. Claims backed only by a public reference carry `source_url` instead and an empty `source_filenames`.

### `GET /api/chat/messages?limit=200`
The most recent `limit` persisted turns, **oldest first**, for rebuilding the conversation after a reload.
```json
[
  { "id": "…", "role": "user", "content": "What is my LDL?", "claims": null, "created_at": "2026-10-04T13:00:00Z" },
  { "id": "…", "role": "assistant", "content": "Your LDL is 112 mg/dL.", "claims": [ { "statement": "…", "status": "DERIVED", "confidence": 0.75, "…": "…" } ], "created_at": "…" }
]
```

---

## 3. Documents

### `POST /api/documents/upload`
Accepts `multipart/form-data` with field `file` (PDF, PNG, JPEG). Streams upload with a 25MB safety cap (`UPLOAD_MAX_SIZE_BYTES`), saves original artifact to disk as `{uuid4}.{ext}`, writes row to PostgreSQL `documents` table, and queues background ML ingestion — follow it with `GET /api/documents/{id}/events` (SSE) below instead of polling. Do **not** also call `/process`: upload already queues processing.

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

### `DELETE /api/documents/{document_id}`
Removes a document everywhere it was written: its Chroma chunks, its Neo4j facts (observations, medications, conditions, the `Document` node), the stored file, and the Postgres row. `204` on success; `404` unknown id; `409` while the document is still `processing`. Cleanup errors are **not** swallowed (the endpoint returns `500` and keeps the row so you can retry) — a "deleted" document whose facts still answer chat would be a silent privacy failure.

### `GET /api/documents/{document_id}/events` (SSE)
Live ingestion progress for one document. `Content-Type: text/event-stream`; browser `EventSource` works (GET). Replays every event published so far, then streams new ones, and closes after the terminal event — so connecting late or reconnecting never misses a stage. A `: keep-alive` comment is sent every 15s of silence.

Each frame is `event: progress` with `data: {"stage": "...", "message": "..."}`. Stages, in order: `queued`, `gpu_wait` (only if another GPU task is running), `gpu` (loading vision models onto the GPU — evicts the chat models), `extract` (lift reading the document, ~1 min), `index` (embedding passages — loads chat models back), `graph` (writing labs/medications/conditions), then terminal `processed` (message `"Done"`) or `failed` (message = the error text). Returns `404` for an unknown id. History lives in backend memory: for a document with none (e.g. after a backend restart) the stream emits one event carrying its stored status and closes.

### `GET /api/documents`
All uploaded documents, newest first (`DocumentRead[]`, same shape as `GET /{document_id}`). The documents page uses this as its source of truth (no more `localStorage`).

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
Hybrid BM25 + dense MedCPT search fused with Reciprocal Rank Fusion ($k=60$) over a wide candidate pool (max(20, 4×`top_k`)), then reranked with the same cross-encoder + authority + recency scoring chat uses (`app/services/evidence_search.py`). Results are returned best-first.

`score` is the **MedCPT cross-encoder relevance in [0, 1]** (sigmoid of its logit) for that passage against the query — not the combined rank score. It is near 1.0 for clearly relevant passages and drops for marginal ones (e.g. 0.66, 0.40, 0.13), so when every hit is relevant they all show ~100%. `source_filename` is the name the user uploaded, not the stored `<uuid>` name.

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
Request-body equivalent of the search endpoint (same retrieve → rerank → scored citations): `{"query": "...", "top_k": 5}` → `{"citations": [...]}`.

### `POST /api/evidence/verify`
Retrieves candidate evidence for a standalone claim string and executes BART-large-MNLI NLI verification inside `gpu_mode(CHAT)`.

**Request**: `{"claim": "Patient was prescribed Metformin 500mg daily."}`  
**Response**: `{"claim": { ...Claim shape... }}`

### `POST /api/claims/extract`
Standalone atomic claim extraction using the local chat model (`medgemma:4b`). Returns claims with status `UNCERTAIN` and `confidence: null` (extraction only, no verification).

**Request**: `{"text": "Patient has hypertension and elevated LDL."}`  
**Response**: `{"claims": [ { "statement": "Patient has hypertension.", "status": "UNCERTAIN", ... } ]}`

---

## 6. Recommendations

### `GET /api/recommendations/fitness`
### `GET /api/recommendations/nutrition`
Both endpoints currently return **`501 Not Implemented`** (`detail: "ml.recommendations.* not implemented yet"`) while recommendation ML models are under development.
