# PHIRE: Engineering Backlog — Known Gaps, Tech Debt, Open Design Questions

**Status**: Living document. Distinct from `docs/AGGRESSIVE_ROADMAP.md`
(feature build checklist) — this tracks things that already exist but
have a known limitation, a deferred fix, or an undecided design question,
surfaced through code review, audits, and live testing. Update this as items are
resolved or new ones are found; don't let it silently go stale.

**As of**: 2026-09-03, following the full-codebase audit across `frontend/`, `backend/`, `ml/`, and `docker/`.

---

## 1. `frontend/`

- **`frontend/` V1 is implemented** (Next.js 16, React 19, TailwindCSS) with Dashboard (`/`), Medical Chat (`/chat`), Document Ingestion (`/documents`), and Search & Claim Explorer (`/search`).
- **`EvidenceCitation.score` evaluates to `0.0%` in Search UI**:
  `backend/app/services/citations.py:chunk_to_citation()` does not set `score` on `EvidenceCitation` (defaults to `None`), causing `frontend/app/search/page.tsx` to calculate `(null * 100).toFixed(1) => 0.0%`.
- **Document history is isolated to browser `localStorage`**:
  Because backend has no `GET /api/documents` list endpoint, `frontend/app/documents/page.tsx` caches document IDs in `localStorage`. Clearing browser cache or switching devices loses the document list in the UI even though records exist in PostgreSQL.
- **Chat conversation does not persist across page reloads**:
  Chat messages are saved in PostgreSQL `chat_messages` on the backend, but there is no `GET /api/chat/messages` endpoint to rehydrate `frontend/app/chat/page.tsx` upon page load.
- **Duplicate Document Processing Request**:
  `POST /api/documents/upload` automatically adds processing to `BackgroundTasks`, but `frontend/app/documents/page.tsx` immediately invokes `POST /api/documents/{id}/process`, frequently receiving `409 Conflict: "Document is already being processed."`.
- **TypeScript Type Contract Gaps in `frontend/lib/api.ts`**:
  - `Claim.source_span` is typed as `string | null` instead of `[number, number] | null` (matching backend tuple `[start, end]`).
  - `ObservationRead.value` and `ObservationRead.observed_date` are typed non-nullable, but backend condition records return `value: null`.
- **Missing observation status badge**:
  Condition and medication statuses (e.g. `"active"`, `"continued"`) are not displayed alongside values in `frontend/app/page.tsx`.
- **No automated test harness** on `frontend/` (Jest/Vitest/Playwright).

---

## 2. `backend/`

- **No automated test suite**:
  `ml/` has 204 tests (187 passing unit tests + 17 live integration tests) in `ml/tests/`; `backend/` has zero automated tests. A pytest suite with fixtures for all 8 routers is needed.
- **Missing document listing endpoint (`GET /api/documents`)**:
  Needed to query `documents` rows from PostgreSQL to support multi-device/refreshable document management in the frontend.
- **Missing chat history endpoint (`GET /api/chat/messages`)**:
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

- **`PDFTextExtractor` only handles text-based PDFs**:
  A scanned PDF (image-only, no embedded text layer) extracts as empty string today. The designed RapidOCR + `pypdf` router with PyMuPDF rasterization ([`docs/PDF_INGESTION_ROADMAP.md`](PDF_INGESTION_ROADMAP.md)) is pending implementation.
- **Deterministic table extraction (`build_table_observations`) only recognizes olmOCR's `<table>` HTML**:
  Plain `pypdf`-extracted text tables are not recognized deterministically; lab values from text PDFs only reach the graph via prose LLM extraction (`qwen3.5:9b`).
- **`ClaimVerifier.verify()` unbatched sequential inference**:
  `ml/claims/verifier.py` runs one BART-large-MNLI forward pass per evidence chunk sequentially ($O(\text{claims} \times \text{evidence})$), creating high latency on turns with numerous claims. Needs tensor batching.
- **Compound metrics omission (e.g. Blood Pressure)**:
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
