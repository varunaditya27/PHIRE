# CHANGELOG

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-08-15

### Initial Setup & Documentation

**Added**
- Core documentation structure (README, CONTRIBUTING, GET_STARTED, REPO_STRUCTURE)
- Feature specification aligned to research requirements (docs/FEATURES_ALIGNED.md)
- Aggressive implementation roadmap (docs/AGGRESSIVE_ROADMAP.md)
- Open-source tools integration guide (docs/OPEN_SOURCE_TOOLS.md)
- Role division with clear responsibilities across 3-person team

**Team Roles**
- **Varun Aditya**: ML & Intelligence (RAG, claims, evidence attribution, recommendations)
- **Anika U Bhat**: Backend Infrastructure (FastAPI, Ollama, PostgreSQL, Chroma, Docker)
- **M Shashwati Rao**: Frontend & Evaluation (Next.js UI, metrics, benchmarks, research)

**Core Features (MVP - 3 weeks)**
- Local LLM conversational assistant (Ollama + MedGemma 1.5)
- Privacy-preserving data handling (no cloud APIs, encrypted storage)
- Evidence-attributed generation (claim-level verification with sources)
- Longitudinal health reasoning (temporal analysis over years)
- Hallucination detection & abstention (refuse to guess)
- Document processing & ingestion (PDF extraction, normalization)
- Health timeline visualization (interactive, trend-based)
- Fitness recommendations (HAR-based personalization)

**Extended Features (Months 2-9)**
- Nutrition recommendations (ML model trained on real data)
- Computer vision: Food recognition & calorie estimation
- Computer vision: Exercise posture analysis & form feedback
- Wearable integration (Fitbit, Oura, Apple Health, etc.)
- Contradiction detection (conflicting records)
- FHIR-compliant health representation
- Doctor-preparation summaries for clinical appointments

**Technology Stack**
- **LLM**: Ollama + MedGemma 1.5 (8B, 4-bit quantized)
- **Backend**: FastAPI (Python), PostgreSQL with pgvector
- **Vector DB**: Chroma (native Python)
- **Frontend**: Next.js 15 with TypeScript/React
- **Containerization**: Docker + Docker Compose
- **Evidence Attribution**: MedRAGChecker, LangChain
- **ML Training**: PyTorch, TensorFlow, Hugging Face
- **Evaluation**: ArchEHR-QA 2026, scikit-learn

**Open-Source Tools (40+ integrated)**
- RAG & Evidence: MedRAGChecker, Medical Graph RAG, MEGA-RAG, VISA, Docling, Spacy
- Computer Vision: YOLOv8, EfficientNet, MediaPipe Pose, OpenPose
- Food/Nutrition: Recipe1M, Nutrition5k, USDA FoodData Central, Food-101
- Embeddings: Sentence-Transformers, SciBERT, PubMedBERT
- Deployment: Open Wearables (wearable integration), Docker

**Project Structure**
- Flat directory layout (no `src/` wrapper)
- Parallel development paths (zero blocking between team members)
- Clear API contracts between subsystems
- Mock/stub implementation for Week 1 independence

**Success Metrics (MVP)**
- Response latency: <3 seconds end-to-end
- Evidence attribution precision: >85%
- Hallucination rate reduction: >40% vs baseline
- ArchEHR-QA accuracy: >75% claims fully supported
- Zero cloud data egress (privacy audit passes)

**Research Contributions (Publication-Ready)**
- Paper 1 (Month 4-5): Evidence attribution + longitudinal reasoning
- Paper 2 (Month 8-9): Hallucination detection + privacy-utility trade-offs
- Target venues: ACL, EMNLP, NeurIPS, Medical AI conferences
- Reproducible artifacts: Code, benchmarks, datasets

**Key Decisions**
- ✅ Local-only deployment (no cloud APIs)
- ✅ 8B model quantized for local inference
- ✅ Native vector DB (Chroma) for MVP simplicity
- ✅ Evidence-first design (every claim has sources)
- ✅ Three-person team with clear role division
- ✅ Computer vision as Month 2+ extension (not MVP bloat)

**Disclaimer**
PHIRE is NOT a medical device and NOT a substitute for professional medical advice. Designed for wellness and decision-support purposes only.

---

## [0.2.0] - 2026-08-16

### ml/: RAG core, claim verification, and Longitudinal Health Graph

The bulk of `ml/`'s core pipeline landed in this session — retrieval,
reranking, claim extraction/verification, patient document ingestion, and
the first version of the Neo4j-backed graph layer.

**Added**
- Hybrid retrieval: MedCPT dual-encoder embeddings + BM25, fused via
  reciprocal rank fusion (`ml/rag/embeddings.py`, `ml/rag/retriever.py`)
- Reranking: MedCPT cross-encoder + authority/recency scoring, with a
  patient-document floor fix for reference-corpus ties
  (`ml/rag/reranker.py`, benchmarked in `ml/rag/reranker_experiments/`)
- Reference-evidence ingestion: PubMed, MedlinePlus, USDA FoodData Central
  (`ml/rag/ingest/run_ingest.py`)
- `ml/llm/`: Ollama client, prompt templates, context assembly — with
  local-only enforcement (`ml/local_only.py`) shared across every
  Ollama/Neo4j client
- Claim extraction, NLI-based verification (BART-large-MNLI, benchmarked
  against 5 other candidates), and confidence scoring
  (`ml/claims/`, `ml/chains/qa_chain.py`)
- Patient document ingestion: olmOCR-v2 for scanned/photographed
  documents (benchmarked against olmOCR-v1), table-aware chunking, exact
  character-span citation tracking (`ml/rag/ingest/`)
- Longitudinal Health Graph v1: deterministic Observation extraction from
  tables, schema-constrained LLM extraction of prose facts (benchmarked
  hand-rolled extraction vs. Google LangExtract), Medication/Condition
  node types (`ml/graph/`)

**Fixed**
- Security/correctness bugs found in a full `ml/` code review: a
  prefix/substring-based localhost check that a hostname like
  `localhost.attacker.example` could bypass (replaced with proper
  hostname parsing, `ml/local_only.py`); a table/prose observation
  dedup bug that misreported ingested counts

**Docs**
- `docs/ML_HANDOFF_FOR_ANIKA.md` — integration contract for `backend/`
- `docs/GRAPH_SCHEMA_ROADMAP.md` — graph schema, deferred work, trigger conditions

## [0.3.0] - 2026-08-25

### Graph read path, OCR routing, and a correctness/coverage hardening pass

**Added**
- Read path for the graph layer: current patient facts and precomputed
  trend deltas fed into chat generation, with `DERIVED` claim labeling
  for a claim that matches a precomputed trend rather than asking NLI to
  do arithmetic (`ml/graph/patient_context.py`, `ml/chains/qa_chain.py`)
- RapidOCR-based pre-pass to route scanned PDFs to the full olmOCR pass
  only when needed (`ml/rag/ingest/router_experiments/`)
- `ml/tests/test_qa_chain_live_e2e.py` — full pipeline test against real
  Ollama/Neo4j/Chroma/MedCPT/BART-MNLI, no fakes
- 41 new tests across graph unit coverage, verification-pool capping,
  and date-parsing edge cases

**Fixed**
- A privacy-boundary gap: one Ollama call site (`ml/graph/prose_extraction.py`,
  the module handling the most PHI-sensitive free text in the codebase)
  wasn't enforcing the local-only check applied everywhere else
- A document-dating bug: a document listing a patient's date of birth
  before its own service date got every Observation from that document
  silently misdated to the birth year; date parsing is now day-first
  (PHIRE's primary audience is Indian users/clinics — DD/MM/YYYY, not
  the US MM/DD/YYYY convention) and excludes DOB-labeled dates
- Lab-value parsing: negative values (e.g. blood-gas base excess) no
  longer silently fail to parse; a compound systolic/diastolic reading
  ("148/92 mmHg") is now correctly treated as unparseable for this
  schema instead of silently truncating to a corrupted value+unit pair
- An unbounded claim-verification pool — capped so NLI verification cost
  doesn't grow unbounded with patient history
- A live-corpus contamination issue: 21 chunks from earlier OCR-benchmark
  fixture ingestion were sitting in the real Chroma reference store at
  the same authority tier as genuine patient data, found via live
  end-to-end testing
- Dead `langchain` dependency removed from `ml/requirements.txt`
  (never imported — `ml/chains/qa_chain.py` is hand-written orchestration)

**Docs**
- `docs/RESEARCH_LOG.md` added — dated findings/decisions in a form
  reusable for paper drafting
- `ml/README.md` added — `ml/` subsystem overview, quick start, model
  choices, feature status
- README.md, REPO_STRUCTURE.md, CONTRIBUTING.md, GET_STARTED.md,
  `docs/FEATURES_ALIGNED.md`, `docs/AGGRESSIVE_ROADMAP.md`,
  `docs/GRAPH_SCHEMA_ROADMAP.md`, `docs/OPEN_SOURCE_TOOLS.md`, and
  `docs/PHIRE_STRUCTURED_GRAPH_MEDICAL_CORPUS_IMPLEMENTATION.md` audited
  and corrected for staleness (stale tool references from initial
  planning — MedRAGChecker, LangChain, MedGemma "1.5"/"8B", pgvector,
  Docling — that were superseded by what was actually built but never
  updated in these docs)

## [0.4.0] - 2026-08-28

### `backend/`: wired to real `ml/` interfaces, full infrastructure

Anika's backend landed in this session — FastAPI routers wired to `ml/`'s
real classes (not stubs), PostgreSQL schema + Alembic migrations, Docker
build/orchestration, and request-level audit logging.

**Added**
- All 8 routers (`chat`, `documents`, `observations`/`timeline`, `search`,
  `evidence`, `claims`, `recommendations`, `health`) wired to `ml/`'s real
  `QAChain`/`HybridRetriever`/`ClaimVerifier`/`OllamaClient`/`GraphClient`
  via cached singletons (`app/services/ml_singletons.py`)
- PostgreSQL schema + Alembic migrations for the single-patient data model
- `AuditMiddleware` (`app/security.py`) — request-level audit trail for
  every patient-data-facing endpoint
- Docker build (`ml/` + `backend/` dependencies in one image) and compose
  orchestration for the full stack (Postgres, Ollama, Neo4j, backend,
  frontend)
- `docs/BACKEND_HANDOFF.md` — integration log: what was retired, fixed,
  tested, and known gaps

**Fixed** (review pass before merge)
- `AuditMiddleware` skipped logging entirely on an unhandled route
  exception (e.g. Neo4j down) — now logs in a `finally`, so a failed
  access to a HIPAA-audited endpoint still leaves an audit trail
- `is_outbound_host_allowed()` (the no-cloud-calls enforcement function)
  was defined but never called anywhere — wired into `/api/health`'s
  Ollama probe, the one HTTP call backend itself makes
- `/api/search` was missing from `_AUDITED_PREFIXES` despite being a GET
  passthrough to the same evidence-retrieval call as the audited
  `/api/evidence/retrieve`
- Document upload buffered the entire file into memory before checking
  the size cap, defeating it as a memory-exhaustion guard — now streamed
  in chunks with the cap enforced as it reads
- `POST /api/documents/{id}/process` had no guard against being triggered
  twice concurrently, letting two calls race and duplicate ingestion work
  — now rejects with `409` if already processing
- `POST /api/evidence/verify` computed confidence with an ad-hoc formula
  instead of `ml.claims.confidence.compute_confidence` (the formula
  `/api/chat` actually uses), collapsing to exactly `0.0` on every
  CONFLICTING verdict — now uses the shared formula
- `/api/health` called `ml_singletons.get_retriever()` to test Chroma
  connectivity, which as a side effect loads the MedCPT embedding model
  into VRAM on first call — now uses a direct `chromadb` client instead,
  so a routine healthcheck no longer risks pinning ~2-3GB of VRAM
- `backend/data/` (a committed Chroma sqlite DB, HNSW index binaries, and
  two sample PDFs — runtime/generated state) was checked into git —
  removed and gitignored

**Fixed** (second pass — the three items `docs/BACKEND_HANDOFF.md` §6
had flagged as known gaps, plus one more found while checking CORS)
- VRAM ordering risk: chat generation and document ingestion could run
  concurrently and OOM an 8GB GPU (each independently loads/uses
  VRAM-resident models) — added `ml_singletons.GPU_LOCK`, held by both
  `router_chat.py`'s chat generation and `document_processor.py`'s
  ingestion pipeline, so they now serialize instead of racing
- `nginx` proxy profile targeted the bridge-network service name
  `backend:8000`, unreachable from a host-networked `backend` — `nginx`
  now runs `network_mode: host` too, targeting `localhost`
- `claims` Postgres table was defined (with a migration) but nothing
  wrote to it — `router_chat.py` now inserts a `Claim` row per claim
  alongside the existing `chat_messages.claims` JSON snapshot
- `backend/.env.example`'s `CHROMA_PERSIST_DIR=./data/chroma` reintroduced
  the cwd-relative-path bug `docs/BACKEND_HANDOFF.md` §5 says was already
  fixed once — `scripts/run_backend.sh` `cd`s into `backend/` before
  launching, so copying the example verbatim silently diverges from
  `ml/`'s own repo-root-relative default. Left unset in the example so
  `config.py`'s correct default applies

**Changed**
- Consolidated the two near-duplicate `docker-compose.yml` files (root +
  `docker/`) into one, `docker/docker-compose.yml` — the root copy is
  retired. All Docker-related files now live under `docker/`: the
  standalone backend build (`backend/Dockerfile` → `docker/Dockerfile.backend.standalone`)
  and the root `.dockerignore` (→ `docker/Dockerfile.backend.dockerignore`,
  picked up via BuildKit's per-Dockerfile ignore-file convention)

**Docs**
- `backend/README.md` added — `backend/` subsystem overview, API surface,
  configuration, quick start (mirrors `ml/README.md`'s structure)
- README.md, REPO_STRUCTURE.md updated for the `backend/README.md`
  reference and the docker-compose.yml consolidation

## [0.5.0] - 2026-08-28

### Final review pass across `backend/` + `ml/` before frontend work begins, plus frontend docs

A full-codebase review (not diff-scoped) of `backend/` and `ml/` together,
run as the gate before `frontend/` work starts. Several of its findings
were regressions in fixes from this same review cycle (`[0.4.0]`) — noted
below.

**Fixed**
- `ml/chains/qa_chain.py`'s `_verify_claim` (and `router_evidence.py`'s
  copy of the same formula) used `next(..., len(evidence))` as a
  rank-not-found fallback, which collides with a genuine rank of 0 when
  the verification pool is empty — a claim with **no** matched evidence
  got `compute_confidence`'s retrieval-only floor (0.25) instead of
  `0.0`. Both now special-case "no evidence" to `confidence = 0.0`
  directly
- `QAChain.answer()` had no error handling around its Neo4j graph calls,
  so any Neo4j outage 502'd every `/api/chat` request — including
  general questions that never needed patient-graph facts, contrary to
  CLAUDE.md describing the graph layer as not MVP-blocking. Graph facts
  now default to empty (with a logged warning) instead of failing the
  request when Neo4j is unreachable
- `document_processor.py` never rolled back Chroma chunks / Neo4j facts
  a failed ingestion had already written before the failure — a document
  shown as `failed` could still have its data served by `/api/search`,
  `/api/evidence/*`, `/api/observations`, and `/api/timeline`. Added
  `HybridRetriever.delete_by_document_id` and `ml/graph/deletion.py`,
  called from the failure path
- `GPU_LOCK` (added in `[0.4.0]` for chat + ingestion) didn't cover
  `router_evidence.py`'s `/retrieve` + `/verify`, `router_search.py`'s
  `/evidence`, or `router_claims.py`'s `/extract`, even though all three
  call the same GPU-resident singletons — now held by all of them
- `AuditMiddleware`'s `finally` block (added in `[0.4.0]` to log on
  unhandled route exceptions) called `log_access()` with no try/except
  of its own — a logging failure (e.g. disk full) replaced the real
  response with an unhandled 500 for every audited-endpoint request.
  Now caught and logged best-effort instead
- `backend/app/security.py` reimplemented `ml/local_only.py`'s
  `require_localhost` as a second hand-written allowlist that had
  already drifted (an extra `"0.0.0.0"` entry absent from `ml/`'s
  canonical set) — now delegates to the shared `ml/` implementation
  directly
- `POST /api/documents/{id}/process`'s concurrency guard (added in
  `[0.4.0]`) was a read-then-write check, not atomic across two
  concurrent HTTP requests/sessions — replaced with a single conditional
  `UPDATE ... WHERE status != 'processing'`, atomic via Postgres row
  locking
- `POST /api/documents/upload` was `async def` but ran blocking disk
  I/O (`mkdir`, `write_bytes`) and a DB commit directly on the event
  loop — offloaded to a threadpool via `run_in_threadpool` so a large
  upload can't stall other concurrent requests
- A failed `/api/chat` pipeline call left the user's already-committed
  `ChatMessage` with no paired assistant reply, contradicting the
  module's own "every exchange is persisted regardless of outcome"
  docstring — now writes an error-marker assistant message on failure
- `backend/.env`'s `PROSE_EXTRACTION_MODEL` was silently ignored —
  `document_processor.py` now threads it through to `extract_facts()`
  instead of relying on that function's own default (`OCR_MODEL` is a
  separate, not-yet-fixed gap — see `docs/BACKEND_HANDOFF.md` §6)

**Tests**
- `ml/tests/test_qa_chain.py`: added coverage for the zero-evidence
  confidence fix and Neo4j-unreachable graceful degradation; fixed an
  existing test (`test_verified_claim_has_no_source_span_when_evidence_lacks_offsets`)
  whose mock evidence chunk was never actually part of the pool passed
  to `verify()` — it only passed before this fix because of the very
  rank-collision bug being fixed
- `ml/tests/test_retriever.py`: added coverage for
  `delete_by_document_id` (removes only the target document's chunks,
  rebuilds BM25, no-ops for an unknown document_id)

**Docs**
- `docs/API_REFERENCE.md` added — full request/response reference for
  every backend endpoint, generated from the actual routers/Pydantic
  models
- `docs/FRONTEND_HANDOFF.md` added — start-here doc for `frontend/`
  work: how to run the stack, what's built, gotchas (no streaming,
  inconsistent id types, GPU-shared backend, etc.)
- README.md, REPO_STRUCTURE.md updated with links to both

## [0.5.1] - 2026-08-28

### Engineering backlog doc + documentation audit

**Docs**
- `docs/BACKLOG.md` added — consolidates known gaps, tech debt, and open
  design questions across `ml/`, `backend/`, and `frontend/` (surfaced
  through the `[0.4.0]`–`[0.5.0]` review passes plus what was already
  tracked in `docs/BACKEND_HANDOFF.md` §6) into one place, distinct from
  `docs/AGGRESSIVE_ROADMAP.md`'s feature checklist
- `docs/AGGRESSIVE_ROADMAP.md`'s Core Build Checklist updated — several
  items (`PostgreSQL`, `FastAPI scaffold`, backend retrieval/chat
  endpoints, HIPAA audit trails, README+deployment docs) were still
  unchecked despite being done as of `[0.4.0]`/`[0.5.0]`
- `README.md`, `REPO_STRUCTURE.md` updated: `docs/BACKLOG.md` linked;
  `REPO_STRUCTURE.md`'s `docs/` tree was also missing
  `docs/BACKEND_HANDOFF.md`, `docs/API_REFERENCE.md`, and
  `docs/FRONTEND_HANDOFF.md` (all added in `[0.4.0]`/`[0.5.0]` but never
  added to the tree listing) — added

## [0.6.0] - 2026-09-09

### Unified Schema-Guided Visual Document Extraction via datalab-to/lift VLM

**Added**
- `ml/rag/ingest/lift_schema.py`: `CLINICAL_DOCUMENT_SCHEMA` and `validate_lift_payload` adhering strictly to Datalab Lift grammar compilation constraints (natural language descriptions, no `enum`/`anyOf`/`oneOf`/`$ref`/`additionalProperties`).
- `ml/rag/ingest/chunk_synthesizer.py`: Option A declarative clinical sentence synthesizer converting structured visual extractions into clean clinical sentences optimized for BART-large-MNLI entailment scoring.
- `ml/rag/ingest/lift_extractor.py`: Single-pass visual extractor supporting multi-page PDFs and images (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`) with 4-bit NF4 quantization on CUDA, graceful CPU fallback, and deterministic mock mode (`PHIRE_MOCK_LIFT=true`).
- `ml/tests/`: Comprehensive unit test suites (`test_lift_config.py`, `test_lift_schema.py`, `test_chunk_synthesizer.py`, `test_lift_extractor.py`, `test_document_processor.py`) expanding test coverage to 200 passing unit tests.

**Changed**
- `backend/app/services/ml_singletons.py`: Added lazy `@lru_cache` `get_lift_extractor()` singleton with `LIFT_MODEL`, `LIFT_DEVICE`, and `PHIRE_MOCK_LIFT` settings.
- `backend/app/services/document_processor.py`: Refactored `process_document` to run `LiftExtractor` and chunk indexing under `GPU_LOCK`, with transactional rollback for both Chroma and Neo4j upon failure.
- `ml/rag/ingest/patient_documents.py` & `ingest_patient_document.py`: Migrated patient document routing and chunking to `LiftExtractor` and `synthesize_patient_chunks`.
- `ml/graph/document_dates.py`: Standardized ISO `YYYY-MM-DD` date normalization for all graph observations, medications, and conditions to prevent timeline sorting corruption.

**Removed**
- Retired obsolete components: `ml/rag/ingest/ocr.py` (olmOCR-2-7B), `ml/rag/ingest/table_parsing.py` (HTML table regex parsing), and `ml/graph/prose_extraction.py` (`qwen3.5:9b` LLM prose extraction), along with their legacy test files.

---

## [0.7.0] - 2026-10-04

### Working end-to-end on an 8GB GPU: real 4-bit lift, LIFT/CHAT GPU modes, SSE progress

First full live run of upload → lift → graph → timeline → chat since the `[0.6.0]` lift merge (previously only unit-tested in mock mode).

**Fixed**
- **Lift was never actually quantized.** `lift.model.InferenceManager.__init__` accepts only `method`; `LiftExtractor` passed `model_name`/`quantization_config`/`device`, got `TypeError`, and its `except TypeError` silently fell back to `InferenceManager(method="hf")` — an unquantized 18GB bf16 load that spilled into CPU RAM. `_get_model()` now builds the 4-bit NF4 model itself (vision tower kept bf16, `device_map={"": 0}`) and injects it into an `InferenceManager`; no silent fallback. Measured: 56s load, 6GiB resident, 6.5GiB peak, 37s to extract; all values of a sample lab PDF correct.
- **`ClaimVerifier` flipped correct claims to `CONFLICTING`.** NLI gave ~1.0 "contradiction" between same-template sentences about different facts (HDL fact vs an LDL claim) and the old "strongest signal in either direction" pick let it outrank the true 0.99 match, dropping the claim (and the actual value) from the answer. A clearly entailing chunk now wins. Trade-off documented in `docs/ML_HANDOFF_FOR_ANIKA.md` §5.
- **`PHIRE_MOCK_LIFT` was read once at import** (module-level default extractor), so setting it later had no effect. `LiftExtractor.mock` is now resolved at call time.
- Lift's weights are freed after every document (`_release_model`).
- Double-processing on upload: the documents page no longer calls `/process` after `/upload` (which already queues processing).

**Added**
- `backend/app/services/gpu_modes.py`: `gpu_mode(LIFT|CHAT, on_progress)` replaces the bare `GPU_LOCK` at all call sites. Lift and the chat group (MedCPT ×2, reranker, BART-MNLI, Ollama's model) are mutually exclusive on the card; switching evicts the other group, staying put is a no-op (warm chat 36s → 5.6s). `move_to(device)` added to `EmbeddingModel`, `Reranker`, `ClaimVerifier`, `HybridRetriever`; devices are now per-instance, not module-level `_DEVICE`.
- **SSE progress.** `POST /api/chat/stream` (events `progress`…`result`|`error`) and `GET /api/documents/{id}/events` (replay-then-live, keep-alive, closes on `processed`/`failed`), via `backend/app/services/progress.py` and `router_chat.run_chat()` (shared by both chat endpoints). `QAChain.answer(on_progress=...)` reports `graph/retrieve/generate/extract/verify`. Additive — `POST /api/chat` is unchanged.
- Frontend: `lib/sse.ts` (fetch-based SSE reader, works for POST), `api.chat.stream` / `api.documents.watch`, `components/progress-steps.tsx` (live step checklist with per-step timer) used by `/chat` and `/documents`; the documents page's 2.5s polling is removed.
- Tests: `ml/tests/conftest.py` (mock lift by default), `test_gpu_modes.py`, `test_progress.py`, verifier regression test, `on_progress` stage-order test, rewritten `_get_model` tests. **220 passing.**

**Docs updated:** `README.md`, `GET_STARTED.md`, `REPO_STRUCTURE.md`, `ml/README.md`, `backend/README.md`, `docs/API_REFERENCE.md`, `docs/BACKEND_HANDOFF.md` (§9), `docs/FRONTEND_HANDOFF.md`, `docs/ML_HANDOFF_FOR_ANIKA.md`, `docs/BACKLOG.md`, `docs/RESEARCH_LOG.md`.

---

## [0.7.1] - 2026-10-04

### Fixes found by the live end-to-end review

**Fixed**
- **Search relevance showed `0.0%`.** `EvidenceCitation.score` was never set. `GET /api/search/evidence` and `POST /api/evidence/retrieve` now go through `app/services/evidence_search.py`: wide retrieval → the same rerank chat uses → `score` = MedCPT cross-encoder relevance (new public `Reranker.score()`). **Behavior change:** results are now reranked (previously raw fused-rank order), so ordering can differ from before.
- **Users saw `<uuid>.pdf` as a claim's source** (also embedded in chunk text as "Source: …"). `build_chunks(..., filename=)` now carries the original upload name; `document_processor` passes `document.filename`. Previously ingested documents keep the old name until re-uploaded.

**Added**
- `DELETE /api/documents/{id}` (204/404/409-while-processing): removes Chroma chunks, Neo4j facts, the stored file and the Postgres row; errors propagate rather than being swallowed. Documents page gets a delete button (`api.documents.remove`). Verified live: after deleting both test documents Chroma returned to its 623 reference chunks and the graph to 0 observations.
- Tests: `test_evidence_search.py`, filename-override test; **222 passing.**

**Docs updated:** `docs/API_REFERENCE.md`, `docs/BACKLOG.md`, `docs/FRONTEND_HANDOFF.md`, `backend/README.md`, `REPO_STRUCTURE.md`.

---

## [0.7.2] - 2026-10-04

### Persistence, blood pressure, citations

**Added**
- `GET /api/documents` (list, newest first) and `GET /api/chat/messages` (oldest first). The documents page now loads from the backend instead of `localStorage`; the chat page rebuilds the conversation on mount.
- Blood pressure is numeric: `build_lift_observations` adds `Blood Pressure (Systolic)` and `(Diastolic)` observations alongside the compound `148/92 mmHg` one (kept for display and NLI). The dashboard charts them and chat reports systolic/diastolic trend deltas; the dashboard skips series with no numeric readings. Re-ingest documents to get the components for older uploads.
- Chat `citations` is populated from `QAChain`'s new `ChatResponse.evidence` (the reranked passages the answer was drafted from).
- Patient-record claims now cite their source document: graph fact queries join the `Document` node's filename (`get_current_patient_facts_with_sources`) and `QAChain` puts it in the verification chunk's metadata. `DERIVED` (trend) claims intentionally have no single source.
- Tests: observation splitting, fact sources, evidence exposure; **227 passing.**

**Docs updated:** `docs/API_REFERENCE.md`, `docs/BACKLOG.md`, `docs/FRONTEND_HANDOFF.md`, `docs/ML_HANDOFF_FOR_ANIKA.md`, `backend/README.md`.

---

## [0.7.3] - 2026-10-04

### All sources cited, composite readings, reset script

**Added**
- **Every claim cites all its source documents.** `VerifiedClaim.source_filenames` / API `Claim.source_filenames` (plus `claims.source_filenames` JSONB column, Alembic `a1c4e7f9b2d3`). `get_trend_facts_with_sources` attaches both readings' filenames (deduplicated), so a trend claim now cites e.g. `["sample_lab.pdf", "scan2.png"]`; `source_filename` stays as the first for older clients. Chat and search UIs list every file and the reference URL; `Claim.source_span` is now typed `[number, number]`.
- `ml/graph/composite_readings.py`: registry of composite readings chosen from common clinical practice (LOINC BP panel, Snellen, ft/in) — blood pressure with optional pulse → systolic/diastolic/heart rate; Snellen `20/40` → decimal; `5'9"` → cm. Base-name matching keeps qualifiers (`(right eye)`, `(sitting)`) on derived observations. Unregistered `a/b` values (ratios) are never split. New aliases in `metric_resolver`: Heart Rate, Visual Acuity, Height. Verified on a real lift extraction.
- `scripts/reset_data.py`: wipes Postgres (`documents`, `chat_messages`, `claims`, `audit_log`), the Neo4j graph, Chroma patient chunks and uploaded files/audit log for a clean start. `--dry-run`, typed `RESET` confirmation (or `--yes`), `--keep-audit`, `--include-reference` (reference corpus kept by default). Verified end-to-end on a scratch Postgres/Neo4j/Chroma, never on dev data.
- Tests: composite registry (28), source-filename propagation, reset script on temp dirs; **259 passing**.

**Docs updated:** `README.md` (reset section), `REPO_STRUCTURE.md`, `docs/API_REFERENCE.md`, `docs/BACKLOG.md`, `docs/ML_HANDOFF_FOR_ANIKA.md`, `ml/README.md`.

---

## [0.7.4] - 2026-10-04

### Batched claim verification

`ClaimVerifier._predict_batch` replaces the per-chunk `_predict` loop. Pairs are tokenized once, sorted by length, and packed into batches under a token budget (`BATCH_TOKEN_BUDGET=2048`, `MAX_BATCH_PAIRS=32`); results are restored to input order. A first fixed-size-batch version was *slower* on small pools (all pairs landed in one batch and short patient facts were padded to a 512-token passage), hence the token budget.

**Measured on the real BART-large-MNLI (RTX 5050, 3 claims):** results match the old loop (max probability difference 4.8e-6, identical statuses); typical turn (15 pairs) ≈ 1.0× (no gain, no loss); worst-case pool (105 pairs) ≈ 1.9–2.7× faster; peak VRAM 1.9GiB. The gain is smaller than first expected because time is dominated by the long 512-token passages (compute-bound), not per-call overhead.

**Not applied (needs a decision):** fp16 inference measured a further ~2.3× on the worst case with max probability difference 0.003 and 0/315 status flips, and halves the model's VRAM, but changes numerics.

Tests: pool-packing and order-restoration tests; **261 passing.** Docs updated: `BACKLOG`, `BACKEND_HANDOFF`, `CODEBASE_AUDIT`.

---

## [0.7.5] - 2026-10-04

### fp16 claim verification on CUDA

`ClaimVerifier` now runs BART-large-MNLI in fp16 on CUDA (fp32 on CPU; `move_to` converts in step with the device; softmax computed in fp32). Checked on the 129 hand-labeled pairs (`ml/claims/experiments/eval_data`): accuracy vs gold 0.9690 both ways, 0 argmax-label flips, 0 threshold-status flips, max probability difference 0.0024, pairs sitting at a threshold unchanged. Steady-state typical turn (15 pairs × 3 claims) 1.27s → 0.40s (~3.1×); worst-case pool (105 pairs × 3) ≈ 0.9s vs 7.2s for the original sequential fp32 loop. Peak model VRAM 1.9 → 1.6GiB. Drawback: ~2s one-time kernel warmup on the first verification after startup. Test: `test_place_uses_fp32_on_cpu_and_fp16_on_cuda`.

---

## [0.8.0] - 2026-10-04

### Docker deployment audited end to end, built and run for real

Verified on a throwaway Compose project (own ports, volumes, data dir; dev stack untouched): fresh database → auto-migration → document upload through lift inside the container (GPU visible, non-root) → SSE → chat → reference-corpus claim → backend restart persistence → nginx proxy. `docker/` is Anika's folder; these are cross-folder changes to hand over.

**Fixed (each was a real defect)**
- The backend image could not be built at all: `lift-pdf` needs Python >= 3.12, the image was 3.11 (broken since `[0.6.0]`). Now `python:3.12-slim`.
- Compose read `.env` from `docker/`, not the repo root, so the documented root `.env` (ports, passwords, model) was silently ignored. Everything now goes through `--env-file .env` (`scripts/run.sh` does it).
- `ml/` bind mount was unreadable on SELinux hosts (Fedora) — `ml/` is now baked into the image; the remaining bind mounts carry `:z`.
- No migrations at container start — `docker/backend-entrypoint.sh` runs `alembic upgrade head` (retrying) then uvicorn.
- `NEXT_PUBLIC_API_URL` was set at runtime, where Next ignores it — now a build arg; `frontend/lib/api.ts` uses `??` so an empty value means same-origin. Missing `frontend/.dockerignore` meant host `node_modules`/`.env.local` were copied into the build.
- No GPU: `docker/docker-compose.gpu.yml`, layered on automatically by `scripts/run.sh` when an NVIDIA runtime exists.
- Privacy: DB/Ollama/frontend ports and the backend were published on all interfaces with no authentication — all now bound to `127.0.0.1`; LAN access is an explicit opt-in (`proxy` profile + `BACKEND_HOST`). Backend runs as non-root. `CORS_ORIGINS` follows `FRONTEND_PORT`.
- nginx: 1MB upload cap (413 on every real PDF), no SSE-safe settings, hardcoded ports, IPv6 `localhost` refusals — now `docker/nginx.conf.template` (templated ports, 25MB, unbuffered SSE, `127.0.0.1`).
- Cold-start race, reproduced in Docker: a document ingesting while a chat arrives on a fresh backend failed (`cannot import name 'AutoModel' from 'transformers'`, Chroma `KeyError`). `preload_ml_modules()` imports ml's heavy modules once at startup (lifespan) and the failure rollback now takes the GPU lock. Tests added.
- `pgvector/pgvector:pg16` replaced by `postgres:16` — pgvector was never used (Chroma is the vector store); the dev DB had only `plpgsql`.
- The broken ml/-free `Dockerfile.backend.standalone` was removed (backend cannot run without `ml/`).

**Added**
- Ollama: the backend uses the **host's** Ollama by default (`OLLAMA_HOST`); the bundled container (`ollama` + one-shot `ollama-pull`) is opt-in (`--profile ollama`), enabled by `scripts/run.sh` only if no host Ollama is found. Stale `qwen3.5:9b` pull instructions removed — only `medgemma:4b` is used.
- `ingest` profile to seed the public reference corpus; healthchecks and `depends_on` ordering; `restart: unless-stopped`; `scripts/run.sh` rewritten (GPU/Ollama detection, health wait, `down`); new `.env.example` variables (`PHIRE_UID/GID`, `PHIRE_DATA_DIR`, `HF_CACHE_DIR`, `OLLAMA_MODELS_DIR`, `BACKEND_HOST`, `PROXY_PORT`, `NEXT_PUBLIC_API_URL`).
- Tests: `preload_ml_modules`, rollback-under-lock; **264 passing.**

**Docs updated:** `README.md`, `GET_STARTED.md`, `REPO_STRUCTURE.md`, `docs/BACKEND_HANDOFF.md` (§8 Docker; GPU/SSE section renumbered §9), `docs/BACKLOG.md`, `docs/CODEBASE_AUDIT.md`, `docs/API_REFERENCE.md`, `.env.example`.

---

## [0.8.1] - 2026-10-04

### Frontend end-to-end review (real Chrome, against the Docker stack) and fixes

Every page was driven with `playwright-core` + system Chrome against the running Docker stack: dashboard, chat (history rehydration, live SSE steps, answer/claim audit), documents (unsupported-type error, upload with live progress, reload persistence, delete with confirm), search (both tabs), dark mode and a 390px viewport; console errors, failed requests and every API call were captured (all 2xx, no console problems). Findings fixed:

- **Dashboard showed units twice** ("51 mg/dL mg/dL", "132/84 mmHg mmHg"): `value` already carries the unit. `lib/readings.ts` splits it once.
- **One shared chart axis** flattened HbA1c (~6) against blood pressure (~140), and the 5-colour palette repeated across 7 series (two pairs identical; the darkest ink vanished in dark mode). Now one chart per unit (`components/timeline-chart.tsx`) with an 8-colour palette legible on both themes.
- **"Recent Observations" listed all 24 readings** including superseded ones: now "Latest Readings" (latest per metric, newest first); medications/conditions show their status; `ObservationRead.value`/`observed_date` typed nullable.
- **Documents badge read "Uploaded" for the whole 1–2 minute run** while the checklist showed progress: it now follows the live stream (and hides Delete mid-run).
- **Not usable on a phone**: the fixed 256px sidebar left 134px for content. Below `md` it is now a top bar; page paddings are responsive (no horizontal overflow on any page at 390px).
- **No medical disclaimer anywhere** in the UI: added to the sidebar and under the chat input.
- Search/verifier public sources are now links; a null match score no longer renders as "0.0%".
- Chat answers joined claims without punctuation ("…2026-03-12 HbA1c was 5.8%…"): `QAChain` now ends each claim with a sentence terminator. Test added.

Remaining frontend gaps and ideas are listed in `docs/BACKLOG.md` §1 (reference-corpus text spacing, chat clear/timestamps, stream abort, chart range filter, accessibility pass, committed e2e tests). **265 tests passing.**

**Docs updated:** `docs/FRONTEND_HANDOFF.md`, `docs/BACKLOG.md`, `REPO_STRUCTURE.md`.

---

## Future Versions

See `docs/AGGRESSIVE_ROADMAP.md` for the extended-phase checklist beyond core scope.

