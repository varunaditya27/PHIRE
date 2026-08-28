# PHIRE API Reference

Generated from the actual routers/Pydantic models on `backend/` as of this
doc's last update (see git blame) — not hand-maintained prose, so trust
this over any older description. For live, always-current detail (exact
validation rules, try-it-out), run the backend and hit `GET /openapi.json`
or `/docs` (FastAPI's auto-generated Swagger UI) directly — this doc is the
fast-reference version of the same contract.

**Base URL**: `http://localhost:8000` (Docker or local run — see
[backend/README.md](../backend/README.md)'s Quick Start). No path prefix
beyond `/api`; no versioning yet.

**Auth**: none. PHIRE runs single-user, local-only — no login, no tokens,
no `patient_id` anywhere (see `backend/app/database/schemas.py`'s module
docstring). Every request is audited server-side for patient-data
endpoints regardless (`app/security.py`'s `AuditMiddleware`); nothing
frontend needs to send for that.

**Errors**: standard FastAPI/Pydantic shape, `{"detail": "..."}` for a
plain message or `{"detail": [...]}` for a 422 validation error (array of
`{"loc", "msg", "type"}`). Status codes used: `404` (not found), `409`
(document already processing), `413` (upload too large), `415`
(unsupported file type), `422` (validation), `501` (recommendation model
not implemented yet), `502` (the `ml/` pipeline itself raised — Ollama
down, Neo4j down, etc).

**Content type**: `application/json` for every request/response except
`POST /api/documents/upload`, which is `multipart/form-data`.

---

## Health

### `POST /api/health`
Liveness/readiness check — Postgres, Ollama, Chroma, Neo4j.

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
Bare liveness check, no dependency verification. `{"status": "ok"}`.

---

## Chat

### `POST /api/chat`
The core Q&A endpoint: retrieval → rerank → generate → claim extraction →
verification → confidence scoring → abstention. Single blocking call, **no
streaming** — expect multi-second latency (real LLM + NLI verification per
claim), design the UI around a loading state, not incremental tokens.

**Request** `ChatRequest`
```json
{ "message": "What was my most recent LDL cholesterol level?" }
```

**Response** `ChatResponse`
```json
{
  "id": "…uuid…",
  "answer": "Your most recent LDL cholesterol level was 162 mg/dL.",
  "claims": [
    {
      "id": null,
      "statement": "Your most recent LDL cholesterol level was 162 mg/dL.",
      "status": "DERIVED",
      "confidence": 0.866,
      "source_url": null,
      "source_filename": null,
      "source_span": null
    }
  ],
  "citations": [],
  "created_at": "2026-08-28T12:00:00Z"
}
```
- `claims[].status` is one of `SUPPORTED`, `DERIVED`, `INFERRED`,
  `UNCERTAIN`, `CONFLICTING`, `UNSUPPORTED`. `DERIVED` means the claim
  matched a precomputed trend fact (PHIRE did arithmetic, not the LLM);
  `SUPPORTED` means it's backed by a specific document/reference passage
  (check `source_filename`/`source_url`/`source_span`).
- **The answer text is already filtered to only claims that passed
  verification** — if nothing clears the confidence threshold, `answer`
  is a fixed abstention message and `claims` may be empty. Don't re-filter
  by confidence client-side; do surface `claims` so the user can see what
  was checked and why (or wasn't).
- `citations` is declared on the response model but **not currently
  populated by `/api/chat`** — always `[]` today. Use
  `claims[].source_*` fields for citations instead, or call
  `POST /api/evidence/retrieve` separately if you need a citation list
  independent of an answer.
- `502` if the underlying `ml/` pipeline raises (e.g. Neo4j unreachable).

---

## Documents

### `POST /api/documents/upload`
`multipart/form-data`, field name `file`. Accepts PDF/PNG/JPEG. Returns
immediately with status `uploaded`; ingestion (OCR if needed, chunking,
embedding, graph fact extraction) runs in the background — poll
`GET /api/documents/{id}` for `processed`/`failed`.

**Response** `DocumentUploadResponse` (`201`-equivalent, actually `200`)
```json
{ "id": "…uuid…", "filename": "labs.pdf", "status": "uploaded" }
```
- `413` if the file exceeds `UPLOAD_MAX_SIZE_BYTES` (default 25MB).
- `415` if `content_type` isn't `application/pdf`, `image/png`, or
  `image/jpeg`.

### `POST /api/documents/{id}/process`
Re-run ingestion for an already-uploaded document (e.g. after a fix). 
`409` if it's currently `processing` — don't retry-loop on that, it means
a run is already in flight.

### `GET /api/documents/{id}`
**Response** `DocumentRead`
```json
{
  "id": "…uuid…",
  "filename": "labs.pdf",
  "content_type": "application/pdf",
  "status": "processed",             // uploaded | processing | processed | failed
  "uploaded_at": "2026-08-28T12:00:00Z",
  "processed_at": "2026-08-28T12:00:05Z",
  "error_message": null              // populated only when status == "failed"
}
```
Poll this after upload. No push/websocket notification — frontend owns the
polling interval.

---

## Observations & Timeline

Both read live from the Neo4j graph, not Postgres — there's no
`patient_id`, PHIRE is single-patient per instance.

### `GET /api/observations`
Query params (all optional): `type` (`lab`|`medication`|`condition`|
`symptom`|`vital`), `start_date`, `end_date` (ISO dates; `422` if
`start_date > end_date`).

**Response** `list[ObservationRead]`
```json
[
  {
    "id": "…string, not a UUID…",
    "document_id": "…string or null…",
    "type": "lab",
    "name": "LDL Cholesterol",
    "value": "162",
    "value_numeric": 162.0,
    "unit": "mg/dL",
    "reference_range": "0-100",
    "interpretation": "high",
    "status": null,                 // set for medications/conditions (e.g. "active"), null for labs
    "observed_date": "2026-08-20"
  }
]
```
**`id`/`document_id` are strings, not UUIDs** — they're graph-node ids
derived from source content, not database rows. Don't parse them as UUIDs
client-side.

### `GET /api/timeline`
No query params — returns every series.

**Response** `TimelineResponse`
```json
{
  "series": [
    {
      "name": "LDL Cholesterol",
      "type": "lab",
      "points": [
        { "observed_date": "2025-08-01", "value_numeric": 140.0, "value": "140", "unit": "mg/dL", "observation_id": "…" },
        { "observed_date": "2026-08-20", "value_numeric": 162.0, "value": "162", "unit": "mg/dL", "observation_id": "…" }
      ]
    }
  ],
  "generated_at": "2026-08-28T12:00:00Z"
}
```
One series per distinct observation `name`+`type` — this is what a trend
chart should map directly to (one series = one line).

---

## Evidence & Claims

### `GET /api/search/evidence?query=...&top_k=5`
Hybrid (BM25 + semantic) evidence search — same underlying call as
`POST /api/evidence/retrieve`, exposed as a GET for simple search UIs.

**Response** `list[EvidenceCitation]`
```json
[
  {
    "evidence_passage_id": "patient_doc_<hash>_0",
    "document_id": "…string or null…",
    "text": "…passage text…",
    "source_url": null,
    "source_filename": "labs.pdf",
    "authority": 1.0,
    "page_number": null,
    "score": 0.83
  }
]
```
`evidence_passage_id`/`document_id` are source-derived strings, not
database UUIDs — same caveat as observations above.

### `POST /api/evidence/retrieve`
Same as the GET above, request-body form: `{"query": "...", "top_k": 5}` →
`{"citations": [...]}` (same `EvidenceCitation` shape).

### `POST /api/evidence/verify`
Verify one claim statement against freshly-retrieved evidence (it
re-retrieves internally using the claim text as the query — you don't pass
evidence in).

**Request**: `{"claim": "Metformin 500mg is prescribed twice daily."}`
**Response**: `{"claim": { ...same Claim shape as /api/chat's claims... }}`
- `confidence` is exactly `0.0` when `status` is `UNSUPPORTED` with no
  matched evidence at all (not just low-scoring evidence) — that's a
  deliberate floor, not a rounding artifact; don't treat `0.0` as
  "unknown" and hide it differently than a genuinely low score.

### `POST /api/claims/extract`
Decompose free text into atomic claim statements — **extraction only, no
verification**. Every returned claim has `status: "UNCERTAIN"` and
`confidence: null` by construction; don't treat that status as a real
verdict. Call `/api/evidence/verify` per claim if you need one.

**Request**: `{"text": "Patient has type 2 diabetes and elevated LDL."}`
**Response**: `{"claims": [{"statement": "...", "status": "UNCERTAIN", ...}, ...]}`

---

## Recommendations

### `GET /api/recommendations/fitness`
### `GET /api/recommendations/nutrition`

Both currently return **`501`** — the underlying `ml/recommendations/*`
modules don't expose a `recommend()` function yet (nutrition is
post-MVP/stub; fitness's HAR model isn't wired to this endpoint yet
either). No stable response shape to document — treat both as
not-yet-available and design the UI to handle `501` gracefully (hide the
feature, not crash), not as a bug to work around.

---

## Things to know before wiring the frontend

- **No streaming anywhere.** `/api/chat` in particular can take several
  seconds (real LLM generation + per-claim NLI verification) — build a
  loading/spinner state, not a token-by-token UI.
- **IDs are inconsistent by design, not by accident.** `Document`/`Claim`/
  `ChatMessage` ids are real Postgres UUIDs. `Observation`/evidence
  citation ids are content-derived strings from `ml/`'s Neo4j graph and
  Chroma store. Don't assume every `id` field parses as a UUID.
  See `app/models/observation.py`'s and `app/models/response.py`'s
  docstrings for why.
- **`/api/documents/*` requires polling** — no push notification for when
  processing finishes.
  - **GPU-shared backend**: chat generation, document ingestion, and the
  evidence/claims endpoints all now serialize against each other
  server-side (`ml_singletons.GPU_LOCK`) to avoid a GPU OOM on the dev
  box — a request sent while another GPU-heavy request is in flight will
  simply wait a bit longer, not error. No special frontend handling
  needed, just don't assume every request is equally fast when several
  are in flight at once.
  - **A `failed` document is fully cleaned up, not just marked failed.**
  If ingestion errors out after partially indexing a document, the
  backend rolls back whatever it already wrote to Chroma/the graph —
  `/api/search`, `/api/evidence/*`, `/api/observations`, and
  `/api/timeline` won't return data from a document whose status you're
  showing as `failed`.
  - **`recommendations` endpoints are not usable yet** — see above.
