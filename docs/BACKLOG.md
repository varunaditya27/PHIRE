# PHIRE: Engineering Backlog — Known Gaps, Tech Debt, Open Design Questions

**Status**: Living document. Distinct from `docs/AGGRESSIVE_ROADMAP.md`
(feature build checklist) — this tracks things that already exist but
have a known limitation, a deferred fix, or an undecided design question,
surfaced through code review, audits, and live testing. Update this as items are
resolved or new ones are found; don't let it silently go stale.

**As of**: 2026-10-04, after the first real-model end-to-end run (lift 4-bit, GPU modes, SSE). Items marked ~~struck~~ were resolved in `CHANGELOG.md` `[0.7.0]` and are kept one cycle for traceability. Earlier baseline: 2026-09-03 full-codebase audit.

---

## 1. `frontend/`

- **`frontend/` V1 is implemented** (Next.js 16, React 19, TailwindCSS) with Dashboard (`/`), Medical Chat (`/chat`), Document Ingestion (`/documents`), and Search & Claim Explorer (`/search`).
- ~~**`EvidenceCitation.score` evaluates to `0.0%` in Search UI**~~ (fixed `[0.7.1]`: `/api/search/evidence` and `/api/evidence/retrieve` now rerank and return the cross-encoder relevance as `score`; via `app/services/evidence_search.py`). Original:
  `backend/app/services/citations.py:chunk_to_citation()` does not set `score` on `EvidenceCitation` (defaults to `None`), causing `frontend/app/search/page.tsx` to calculate `(null * 100).toFixed(1) => 0.0%`.
- ~~**Document history is isolated to browser `localStorage`**~~ (fixed `[0.7.2]`: `GET /api/documents`). Original:
  Because backend has no `GET /api/documents` list endpoint, `frontend/app/documents/page.tsx` caches document IDs in `localStorage`. Clearing browser cache or switching devices loses the document list in the UI even though records exist in PostgreSQL.
- ~~**Chat conversation does not persist across page reloads**~~ (fixed `[0.7.2]`: `GET /api/chat/messages` + rehydration on mount). Original:
  Chat messages are saved in PostgreSQL `chat_messages` on the backend, but there is no `GET /api/chat/messages` endpoint to rehydrate `frontend/app/chat/page.tsx` upon page load.
- ~~**Duplicate Document Processing Request**~~ (fixed `[0.7.0]`: documents page no longer calls `/process` after `/upload`; it follows `GET /api/documents/{id}/events`). Original description:
  `POST /api/documents/upload` automatically adds processing to `BackgroundTasks`, but `frontend/app/documents/page.tsx` immediately invokes `POST /api/documents/{id}/process`, frequently receiving `409 Conflict: "Document is already being processed."`.
- **TypeScript Type Contract Gaps in `frontend/lib/api.ts`**:
  - `Claim.source_span` is typed as `string | null` instead of `[number, number] | null` (matching backend tuple `[start, end]`).
  - `ObservationRead.value` and `ObservationRead.observed_date` are typed non-nullable, but backend condition records return `value: null`.
- **Missing observation status badge**:
  Condition and medication statuses (e.g. `"active"`, `"continued"`) are not displayed alongside values in `frontend/app/page.tsx`.
- **No automated test harness** on `frontend/` (Jest/Vitest/Playwright).

---

## 2. `backend/`

- **SSE progress state is in-process memory** (`app/services/progress.py`): single worker only, history lost on restart (the events endpoint then emits one event with the stored DB status). Multi-worker deployment would need a shared channel (Redis/Postgres LISTEN).
- **No heartbeat/timeout on the chat stream thread**: if the QA chain hangs, the SSE connection stays open until the client disconnects; the worker thread is a daemon and is not cancelled.
- **`GPU_LOCK`/`gpu_mode` is per-process**: two uvicorn workers would each think they own the GPU.

- **No automated test suite** (partial: `ml/tests/test_document_processor.py`, `test_gpu_modes.py`, `test_progress.py` exercise some backend services, but there are no router/HTTP-level tests, including for the two SSE endpoints, which were only verified live with curl/Node):
  `ml/` has 217 tests (200 passing unit tests + 17 live integration tests) in `ml/tests/`; `backend/` has zero automated tests. A pytest suite with fixtures for all 8 routers is needed.
- ~~**Missing document listing endpoint (`GET /api/documents`)**~~ (added `[0.7.2]`; `DELETE` in `[0.7.1]`). Original:
  Needed to query `documents` rows from PostgreSQL to support multi-device/refreshable document management in the frontend.
- ~~**Missing chat history endpoint (`GET /api/chat/messages`)**~~ (added `[0.7.2]`). Original:
  Needed to serve past conversation turns with attached claims to the frontend chat UI.
- **`claims.chat_message_id` Foreign Key lacks an index**:
  `backend/app/database/schemas.py` and Alembic migrations have FK constraints on `claims.chat_message_id`, but lack an explicit database index.
- **`nginx` proxy profile**:
  Runs host-networked matching `backend`, but has not been smoke-tested end-to-end under high-concurrency traffic.
- **The `claims` Postgres table is written to but lacks dedicated analytics endpoints**:
  Claims are queryable via SQL for research evaluation, but no specialized evaluation query router exists yet.
- **Caching layer**:
  Response caching for repeat identical queries has not been implemented.

---

## 3. `ml/`

- **Lift accuracy under 4-bit NF4 is unmeasured.** Verified on one synthetic digital PDF (all values correct). Needs a small labelled set of real scans/photos/multi-page reports to quantify the quantization cost; `lm_head` is quantized too (only the vision tower stays bf16) — if accuracy suffers, keeping `lm_head` bf16 costs roughly +1.5GiB, which would push lift's ~6.5GiB peak to ~8GiB — over this card's usable limit.
- **NLI template-contradiction workaround is a heuristic.** `ClaimVerifier` now lets an entailing chunk beat contradictions from other chunks (fixes correct patient claims being flagged `CONFLICTING` by a different metric's fact), but it can mask a true conflict when another chunk entails the claim. A metric-aware pre-filter (match claim analyte to fact analyte before NLI) would be principled. See `docs/RESEARCH_LOG.md` 2026-10-04 §2.
- **`LiftExtractor` reload cost.** Weights are freed after every document (needed to coexist with chat models), so each upload pays ~56s load. Fine for occasional uploads; revisit if batch upload matters.

- **Scanned PDF Fallback Router (RESOLVED)**:
  - Resolved via `datalab-to/lift` 9.7B parameter VLM integration. The unified visual document extraction pipeline processes both native digital PDFs and scanned/photographed documents directly in a single pass, eliminating the scanned-PDF gap.
- **Table & Prose Observation Extraction (RESOLVED)**:
  - Resolved via `CLINICAL_DOCUMENT_SCHEMA` and `LiftExtractor`. The schema-guided visual extraction retrieves lab values, units, reference ranges, flags, medications, and conditions directly into structured JSON, retiring the brittle regex HTML table parser and Ollama `qwen3.5:9b` prose extraction.
- **`ClaimVerifier.verify()` unbatched sequential inference**:
  `ml/claims/verifier.py` runs one BART-large-MNLI forward pass per evidence chunk sequentially ($O(\text{claims} \times \text{evidence})$), creating high latency on turns with numerous claims. Needs tensor batching.
- ~~**Compound metrics omission (e.g. Blood Pressure)**~~ (fixed `[0.7.2]`/`[0.7.3]`: `ml/graph/composite_readings.py` registry — blood pressure (+ pulse) → systolic/diastolic/heart rate, Snellen acuity → decimal, feet-inches height → cm; unregistered a/b values such as ratios are deliberately left whole). Original:
  `ml/graph/observations.py:_split_value()` explicitly rejects compound strings like `"148/92 mmHg"` returning `(None, None)` to prevent corruption, which omits blood pressure from numeric timeline charts and trend computations.
- **USDA Key-Value NLI false uncertainty**:
  Terse key-value USDA reference text (`"Fish, salmon... per 100g: Protein 24.6 g"`) fails natural-language NLI entailment against conversational claims (`"Salmon is high in protein"` scores 0.301 entailment), causing false `UNCERTAIN` abstentions.
- **`ml/rag/retriever.py` in-memory chunk cache staleness**:
  If a standalone ingestion script writes to Chroma while the backend is running, the in-memory cache may miss chunks.
- **`ml/graph/document_dates.py` falls back to today's date**:
  When no clinical date can be extracted from a document, it defaults to `date.today()`, which can make an old undated document appear as the latest reading.
- **Multi-hop graph-RAG retrieval** is planned but unbuilt (see [`docs/GRAPH_SCHEMA_ROADMAP.md`](GRAPH_SCHEMA_ROADMAP.md)).
- **Fitness & Nutrition recommendation models are stubs**:
  `ml/recommendations/` modules contain research notes only. Backend endpoints return `501 Not Implemented`.

---

## 4. `docker/` & Infrastructure

- **`docker/Dockerfile.backend.standalone` is broken**:
  Builds from `backend/` only and installs only `backend/requirements.txt`. Crashes with `ModuleNotFoundError: No module named 'ml'` on startup because backend strictly requires `ml/`.
- **`docker/Dockerfile.backend` lacks automated startup migrations**:
  Does not run `alembic upgrade head` in its `CMD`, leaving a fresh Docker PostgreSQL instance without tables until manually migrated.
- **`docker/Dockerfile.frontend` missing build argument**:
  Does not declare `ARG NEXT_PUBLIC_API_URL` before `npm run build`, preventing runtime API URL customization in containerized production builds.
- **Missing GPU pass-through in `docker/docker-compose.yml`**:
  Lacks GPU device reservations for `ollama` and `backend`, running inference on CPU inside containers unless configured.
- **Missing repository scripts**:
  `scripts/eval.sh` and `scripts/demo.sh` (listed in `REPO_STRUCTURE.md`) do not exist on disk.
- **Docker Host Networking Platform Nuance**:
  Host networking (`network_mode: host`) is Linux-native. macOS and Windows Docker Desktop require version 4.29+ with host-networking beta enabled.

---

## 5. Cross-Cutting & Research

- **ArchEHR-QA 2026 evaluation (167 expert cases) not started**:
  `evaluation/` directory does not exist in the repository yet.
- **Single-Patient Architecture**:
  The system is designed for single-user local deployment (`DEFAULT_PATIENT_ID = "self"`). No authentication or multi-patient scoping exists across APIs or database schemas.
- **Wearable integration and computer vision** (food recognition, posture analysis) are scheduled for Month 2+ per [`docs/FEATURES_ALIGNED.md`](FEATURES_ALIGNED.md).

---

## 6. Resolved in `[0.7.1]`

- Search relevance `score` was always `null` (UI showed `0.0%`) — now the cross-encoder relevance.
- Claims and chunk text cited the stored `<uuid>.<ext>` filename — `build_chunks(filename=...)` now carries the user's original name. Documents ingested before this fix keep the old name (delete + re-upload to refresh).
- No way to delete a document — `DELETE /api/documents/{id}` + a delete button on the documents page; verified against Chroma, Neo4j, disk and Postgres.

Still open from the same review: blood pressure has no numeric value (not charted), chat `citations` is always `[]` (evidence is in `claims`), graph-fact claims (`DERIVED`) show no `source_filename`, document list / chat history don't persist across devices or reloads.

## 7. Resolved in `[0.7.2]`

Document list and chat history now persist server-side; blood pressure is numeric (charted, trended); chat `citations` is populated; patient-record claims cite their source document. Still open: `DERIVED` claims have no single `source_filename` by design; graph-fact claims for observations ingested before `[0.7.2]` have a filename only if the `Document` node has one (all current writers set it).

## 8. Resolved in `[0.7.3]`

- Every claim cites all its source documents (`source_filenames`), including both readings' files for a trend.
- Composite readings beyond blood pressure (acuity, height, BP with pulse; laterality/posture qualifiers preserved).
- `scripts/reset_data.py` for a clean start (README "Start from scratch").

Still open: compound/composite shapes outside the registry (e.g. orthostatic "supine 148/92, standing 130/80" in one value, paediatric "lb oz" weights, comparator values like `>90`) are left as text; the registry is one dict entry per shape. HbA1c dual units are intentionally one observation (first number = the %).
