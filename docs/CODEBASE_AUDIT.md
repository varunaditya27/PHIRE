# PHIRE Codebase Audit: Features, Inconsistencies, Bugs, and Architectural Decisions

**Audit Date**: September 3, 2026  
**Audited Subsystems**: `frontend/`, `backend/`, `ml/`, `docker/`, `scripts/`, `docs/`  
**Workspace**: `/home/varun/Projects/PHIRE`

---

## 1. Executive Summary

This comprehensive audit surfaces all implemented features, remaining functionalities, data contract inconsistencies, edge-case bugs, and foundational design decisions across the PHIRE repository.

### High-Level Status by Subsystem
- **`frontend/`**: Next.js 16 (App Router, React 19, TailwindCSS) UI is fully implemented with **Dashboard (`/`)**, **Evidence-Attributed Chat (`/chat`)**, **Document Ingestion (`/documents`)**, and **Search & Claim Explorer (`/search`)**.
- **`backend/`**: FastAPI service exposing 8 routers (`health`, `chat`, `documents`, `observations`, `search`, `evidence`, `claims`, `recommendations`) with PostgreSQL persistence, HIPAA audit logging, and `GPU_LOCK` serialization.
- **`ml/`**: Hybrid RAG (MedCPT dual-encoder + BM25 + Cross-Encoder with structural patient floor), reverse-RAG claim extraction (`medgemma:4b`) and NLI verification (`facebook/bart-large-mnli`), and Neo4j Longitudinal Health Graph with temporal trend precomputation.
- **`docker/` & Infrastructure**: Container orchestration via `docker-compose.yml` with host-networking for air-gap privacy enforcement, lazy singleton caching, and fail-safe transactional rollback on document ingestion failure.

---

## 2. Feature & Functionality Inventory

### 2.1 Implemented Features
| Subsystem | Component / Feature | Details & Location |
|---|---|---|
| **Frontend** | Patient Dashboard | Multi-series Recharts health timeline and recent clinical observation cards ([`frontend/app/page.tsx`](file:///home/varun/Projects/PHIRE/frontend/app/page.tsx)). |
| **Frontend** | Medical Chat UI | Conversational interface with per-claim expandable NLI verification badges ([`frontend/app/chat/page.tsx`](file:///home/varun/Projects/PHIRE/frontend/app/chat/page.tsx)). |
| **Frontend** | Document Ingestion UI | Drag-and-drop PDF/image uploader with live SSE ingestion progress (stage checklist) ([`frontend/app/documents/page.tsx`](file:///home/varun/Projects/PHIRE/frontend/app/documents/page.tsx)). |
| **Frontend** | Search & Claim Explorer | Hybrid search explorer and direct single-claim NLI verifier ([`frontend/app/search/page.tsx`](file:///home/varun/Projects/PHIRE/frontend/app/search/page.tsx)). |
| **Backend** | Chat & Reverse-RAG QA | Ingestion, retrieval, generation, atomic claim extraction, NLI verification, and confidence filtering ([`backend/app/api/router_chat.py`](file:///home/varun/Projects/PHIRE/backend/app/api/router_chat.py)). |
| **Backend** | Document Ingestion Engine | Multipart file streaming, 25MB validation, background worker, and Chroma/Neo4j index rollback on failure ([`backend/app/api/router_documents.py`](file:///home/varun/Projects/PHIRE/backend/app/api/router_documents.py), [`backend/app/services/document_processor.py`](file:///home/varun/Projects/PHIRE/backend/app/services/document_processor.py)). |
| **Backend** | Longitudinal Health API | Queries Neo4j for observations, medications, conditions, and builds time-series trends ([`backend/app/api/router_observations.py`](file:///home/varun/Projects/PHIRE/backend/app/api/router_observations.py), [`backend/app/services/graph_reader.py`](file:///home/varun/Projects/PHIRE/backend/app/services/graph_reader.py)). |
| **Backend** | Evidence & Search APIs | Hybrid BM25 + dense retrieval and standalone NLI verification ([`backend/app/api/router_search.py`](file:///home/varun/Projects/PHIRE/backend/app/api/router_search.py), [`backend/app/api/router_evidence.py`](file:///home/varun/Projects/PHIRE/backend/app/api/router_evidence.py)). |
| **Backend** | HIPAA Audit Logging | Dual PostgreSQL `audit_log` and local append-only log file with fail-safe error handling ([`backend/app/security.py`](file:///home/varun/Projects/PHIRE/backend/app/security.py), [`backend/app/services/audit_logger.py`](file:///home/varun/Projects/PHIRE/backend/app/services/audit_logger.py)). |
| **ML** | Hybrid Retrieval & Reranking | MedCPT Query/Article dual encoder + BM25Okapi + MedCPT Cross-Encoder with structural patient floor ([`ml/rag/`](file:///home/varun/Projects/PHIRE/ml/rag/)). |
| **ML** | Reference Ingestors | Live API ingestors for MedlinePlus XML, PubMed NCBI E-utilities, and USDA FoodData Central ([`ml/rag/ingest/`](file:///home/varun/Projects/PHIRE/ml/rag/ingest/)). |
| **ML** | Visual Document Extraction | Schema-guided visual extraction of multi-page PDFs and images via `datalab-to/lift` 9.7B VLM with Option A declarative RAG chunk synthesis ([`ml/rag/ingest/lift_extractor.py`](file:///home/varun/Projects/PHIRE/ml/rag/ingest/lift_extractor.py), [`ml/rag/ingest/lift_schema.py`](file:///home/varun/Projects/PHIRE/ml/rag/ingest/lift_schema.py), [`ml/rag/ingest/chunk_synthesizer.py`](file:///home/varun/Projects/PHIRE/ml/rag/ingest/chunk_synthesizer.py)). |
| **ML** | Longitudinal Health Graph | Neo4j graph client, structured observation/medication/condition builders populated directly from Lift VLM extraction, and trend delta computation ([`ml/graph/`](file:///home/varun/Projects/PHIRE/ml/graph/)). |
| **ML** | Claim Verification | BART-large-MNLI claim verifier with calibrated entailment/contradiction thresholds and confidence formula ([`ml/claims/`](file:///home/varun/Projects/PHIRE/ml/claims/)). |

### 2.2 Remaining & Stubbed Functionalities
1. **Recommendations Subsystem (`ml/recommendations/*`)**:
   - `ml/recommendations/fitness/` (`har_model.py`, `recommendations.py`) and `ml/recommendations/nutrition/` (`meal_generator.py`, `model.py`) are research-note stubs.
   - `GET /api/recommendations/fitness` and `GET /api/recommendations/nutrition` return `501 Not Implemented`.
2. **Multi-Hop Graph-RAG Retrieval**:
   - Query-time relational entity graph traversal (e.g., cross-referencing medication dose changes directly against observation deltas) is documented in [`docs/GRAPH_SCHEMA_ROADMAP.md`](file:///home/varun/Projects/PHIRE/docs/GRAPH_SCHEMA_ROADMAP.md) but unbuilt.
3. **Scanned PDF Fallback Router (RESOLVED)**:
   - **Resolved by `datalab-to/lift` integration**: The 9.7B parameter VLM performs unified single-pass visual document extraction directly on both native digital PDFs and scanned image-only PDFs/photos, rendering OCR routing workarounds obsolete.
4. **Backend Document Listing Endpoint (`GET /api/documents`)**:
   - No route exists to query all uploaded documents from PostgreSQL. The frontend uses a client-side `localStorage` cache workaround.
5. **Chat History Persistence Endpoint (`GET /api/chat/messages`)**:
   - User and assistant messages are stored in the PostgreSQL `chat_messages` table, but no endpoint exists to retrieve chat history into the frontend upon page reload.
6. **Automated Backend & Frontend Test Suites**:
   - `ml/` has 204 tests in `ml/tests/` (187 passing unit tests + 17 live integration tests). `backend/` and `frontend/` currently have zero automated tests.
7. **Evaluation Module (`evaluation/`)**:
   - `REPO_STRUCTURE.md` lists an `evaluation/` directory and scripts (`scripts/eval.sh`, `scripts/demo.sh`), which do not exist on disk.

---

## 3. Inconsistencies & Contract Mismatches

### 3.1 `EvidenceCitation.score` Returns `None`
- **Backend Location**: [`backend/app/services/citations.py:23-32`](file:///home/varun/Projects/PHIRE/backend/app/services/citations.py#L23-L32)
- **Issue**: `chunk_to_citation()` never populates the `score` field, causing `score` to default to `None`.
- **Frontend Impact**: [`frontend/app/search/page.tsx:175`](file:///home/varun/Projects/PHIRE/frontend/app/search/page.tsx#L175) renders `{(cite.score * 100).toFixed(1)}%`, displaying `0.0%` for all hybrid search results.

### 3.2 `Claim.source_span` Type Mismatch
- **Backend**: In [`backend/app/models/claim.py:33`](file:///home/varun/Projects/PHIRE/backend/app/models/claim.py#L33), `source_span: tuple[int, int] | None = None` (serializes to JSON array `[start, end]`).
- **Frontend**: In [`frontend/lib/api.ts:19`](file:///home/varun/Projects/PHIRE/frontend/lib/api.ts#L19), `source_span` is typed as `string | null`.

### 3.3 Redundant Document Processing Request
- **Backend**: [`backend/app/api/router_documents.py:78`](file:///home/varun/Projects/PHIRE/backend/app/api/router_documents.py#L78) automatically spawns a background processing task upon upload.
- **Frontend**: [`frontend/app/documents/page.tsx:98`](file:///home/varun/Projects/PHIRE/frontend/app/documents/page.tsx#L98) sends a redundant `POST /api/documents/{id}/process`, frequently receiving `409 Conflict: "Document is already being processed."`.

### 3.4 Nullable Fields in Observation Contract
- **Backend**: In [`backend/app/models/observation.py:28,34`](file:///home/varun/Projects/PHIRE/backend/app/models/observation.py#L28), `value: str | None = None` and `observed_date: date | None = None` (Condition nodes have `value = None`).
- **Frontend**: [`frontend/lib/api.ts:51,57`](file:///home/varun/Projects/PHIRE/frontend/lib/api.ts#L51) types `value: string` and `observed_date: string` as non-nullable.

---

## 4. Bugs, Failure Modes & Edge Cases

### 4.1 Standalone Backend Dockerfile (`docker/Dockerfile.backend.standalone`)
- **Location**: [`docker/Dockerfile.backend.standalone:L1-L29`](file:///home/varun/Projects/PHIRE/docker/Dockerfile.backend.standalone#L1-L29)
- **Bug**: Builds only from `backend/` context and installs only `backend/requirements.txt`. Because `backend/` now imports `ml.*` singletons, running this container crashes immediately with `ModuleNotFoundError: No module named 'ml'`.

### 4.2 Database Migrations Not Applied on Docker Backend Launch
- **Location**: [`docker/Dockerfile.backend:L43`](file:///home/varun/Projects/PHIRE/docker/Dockerfile.backend#L43)
- **Bug**: `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]` does not run `alembic upgrade head`. Running a clean `docker compose up` on a fresh volume leaves PostgreSQL without tables. (Local script `scripts/run_backend.sh:L22` runs migrations correctly).

### 4.3 Missing Build Argument for Client Next.js Bundle
- **Location**: [`docker/Dockerfile.frontend:L1-L27`](file:///home/varun/Projects/PHIRE/docker/Dockerfile.frontend#L1-L27)
- **Bug**: Next.js bakes `NEXT_PUBLIC_*` variables during `npm run build`. Without declaring `ARG NEXT_PUBLIC_API_URL` during the build stage, runtime environment variables in `docker-compose.yml` are not reflected in client JavaScript bundles.

### 4.4 Missing GPU Pass-Through in Docker Compose
- **Location**: [`docker/docker-compose.yml:L47-L104`](file:///home/varun/Projects/PHIRE/docker/docker-compose.yml#L47-L104)
- **Issue**: `ollama` and `backend` containers do not declare `deploy.resources.reservations.devices` with GPU capabilities, forcing containerized Ollama and PyTorch to execute on CPU.

### 4.5 Unbatched NLI Verification Latency Bottleneck
- **Location**: [`ml/claims/verifier.py:L70-L86`](file:///home/varun/Projects/PHIRE/ml/claims/verifier.py#L70-L86)
- **Issue**: `ClaimVerifier.verify()` iterates through evidence chunks sequentially, executing individual BART-large-MNLI forward passes. Evaluating 8 claims against 50 facts generates 400 sequential model calls.

### 4.6 Compound Clinical Metrics Omission
- **Location**: [`ml/graph/observations.py:L59-L60`](file:///home/varun/Projects/PHIRE/ml/graph/observations.py#L59-L60)
- **Issue**: `_split_value()` intentionally rejects compound strings like `"148/92 mmHg"` (returning `(None, None)`) to prevent parsing corruption. As a result, blood pressure readings are excluded from numeric timeline charts and trend computations.

---

## 5. Architectural & Design Decisions

### 5.1 Host-Networking for Air-Gap Privacy Compliance
`ml.local_only.require_localhost()` strictly validates that outbound service hostnames resolve to `{"localhost", "127.0.0.1", "::1"}` to eliminate DNS rebinding and cloud data egress. To satisfy this inside Docker without custom code exceptions, `backend` and `nginx` run with `network_mode: host` in `docker-compose.yml`.

### 5.2 GPU Residency Modes (`gpu_mode`, wrapping `GPU_LOCK`)
Quantized `datalab-to/lift` (4-bit NF4, ~6.5GiB peak) cannot share an 8GB GPU with the chat-time models (MedCPT ×2, reranker, BART-MNLI, Ollama `medgemma:4b`, ~6.9GB). [`backend/app/services/gpu_modes.py`](file:///home/varun/Projects/PHIRE/backend/app/services/gpu_modes.py)'s `gpu_mode(LIFT|CHAT)` holds the process-wide `GPU_LOCK` from [`ml_singletons.py`](file:///home/varun/Projects/PHIRE/backend/app/services/ml_singletons.py) and, only when the mode changes, evicts the other group (in-process models parked in CPU RAM via `move_to`, Ollama unloaded via its API). Same-mode requests are no-ops. Details: `docs/BACKEND_HANDOFF.md` §8.

### 5.2b SSE progress
`POST /api/chat/stream` and `GET /api/documents/{id}/events` stream stage-level progress (frame formats in `docs/API_REFERENCE.md`). Document events come from the in-memory `app/services/progress.py` channel (single-process); chat events from `QAChain.answer(on_progress=...)` via a queue from a worker thread.

### 5.3 Tripartite Data Storage Separation
1. **PostgreSQL**: Upload metadata (`documents`), conversations (`chat_messages`), queryable claim audit rows (`claims`), and access logs (`audit_log`).
2. **Neo4j**: Longitudinal Health Graph (`Patient`, `Observation`, `Medication`, `Condition`, `Document`) for timeline and trend delta computation.
3. **Chroma**: Dense vector collection (`phire_evidence`) storing MedCPT embeddings of OCR and reference chunks.

### 5.4 Reverse-RAG Claim Attribution Pipeline
Rather than streaming unverified LLM output, PHIRE generates a candidate answer, decomposes it into atomic statements via `ClaimExtractor`, verifies each against graph facts and reference passages via `ClaimVerifier` (BART-large-MNLI), and outputs a verified response strictly constructed from claims passing confidence thresholds ($\ge 0.4$).

### 5.5 Fail-Safe Ingestion Rollback
If document processing fails during OCR, table extraction, embedding, or graph writing, `_rollback_ml_writes()` purges partial chunks from Chroma (`delete_by_document_id`) and detached nodes from Neo4j (`delete_document_facts`), guaranteeing that unverified or corrupted data is never served in search or timeline queries.

---

## 6. Actionable Implementation Roadmap

1. **Backend & Frontend Fixes**:
   - In `backend/app/services/citations.py:chunk_to_citation()`, pass `score=getattr(chunk, "score", None)`.
   - Add `GET /api/documents` returning `list[DocumentRead]` in `backend/app/api/router_documents.py`.
   - Add `GET /api/chat/messages` returning `list[ChatMessageRead]` in `backend/app/api/router_chat.py`.
   - Align TypeScript types in `frontend/lib/api.ts` (`Claim.source_span: [number, number] | null`, `ObservationRead.value: string | null`, `ObservationRead.observed_date: string | null`).
   - Remove the duplicate `api.documents.process()` invocation from `frontend/app/documents/page.tsx`.
2. **DevOps & Infrastructure Fixes**:
   - Add an entrypoint wrapper or migration command to `docker/Dockerfile.backend` to run `alembic upgrade head` on startup.
   - Add `ARG NEXT_PUBLIC_API_URL` to `docker/Dockerfile.frontend`.
   - Add GPU resource reservations to `docker/docker-compose.yml`.
   - Retire or fix `docker/Dockerfile.backend.standalone`.
3. **ML Enhancements**:
   - Add batched inference in `ml/claims/verifier.py` to accelerate multi-claim verification.
   - Implement the RapidOCR + `pypdf` scanned PDF fallback router per `docs/PDF_INGESTION_ROADMAP.md`.
   - Implement split parsing for compound metrics (systolic / diastolic blood pressure).
