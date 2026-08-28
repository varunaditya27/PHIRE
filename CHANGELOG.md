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

---

## Future Versions

See `docs/AGGRESSIVE_ROADMAP.md` for the extended-phase checklist beyond core scope.

