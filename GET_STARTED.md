# PHIRE: Ready to Code - Get Started NOW

**Status**: ✅ Core ML, FastAPI Backend, and Next.js Frontend V1 complete and integrated
**Date**: September 2026
**Team**: Varun (ML & Intelligence), Anika (Backend Infrastructure), Shashwati (Frontend & Evaluation)

---

## 📖 READ THESE (In Order)

### 1. **README.md** (7 min)
- What PHIRE is
- Quick start commands
- Tech stack overview
- Disclaimer

### 2. **CONTRIBUTING.md** (20 min) - YOUR ROLE
- **Varun**: ML & Intelligence section (RAG, claims, evidence attribution)
- **Anika**: Backend Infrastructure section (FastAPI, Ollama, PostgreSQL, Docker)
- **Shashwati**: Frontend & Evaluation section (Next.js UI, metrics, benchmarks, research)

### 3. **docs/CODEBASE_AUDIT.md** (15 min)
- Master audit of features, inconsistencies, bugs, and design decisions across all folders.

### 4. **docs/BACKLOG.md** (10 min)
- Known gaps, technical debt, and open items.

### 5. **docs/API_REFERENCE.md** (10 min, reference)
- Complete request/response schemas for all backend endpoints.

---

## 🚀 Setup & Execution

### Running the Stack (Docker)
```bash
bash scripts/run.sh        # creates .env files if missing, builds, starts, waits for health
# first time only -- seed the public reference corpus (needs network):
docker compose --env-file .env -f docker/docker-compose.yml --profile ingest run --rm ingest
curl -X POST http://localhost:8000/api/health
# NOTE: always pass --env-file .env to docker compose (it reads docker/.env otherwise). Details: docs/BACKEND_HANDOFF.md section 8.
```

### Running Locally (Development Mode)
```bash
# Terminal 1: Backend
bash scripts/run_backend.sh

# Terminal 2: Frontend
bash scripts/run_frontend.sh
```

---

## 📅 CORE BUILD STATUS

### Varun - ML & Intelligence
- [x] Download embedding model (medical-specialized) — MedCPT
- [x] Setup Chroma vector DB (in-process)
- [x] Ingest clinical reference documents (MedlinePlus, PubMed, USDA)
- [x] Design LLM prompt for claim extraction (`medgemma:4b`)
- [x] Design claim verification approach — NLI-based (`facebook/bart-large-mnli`)
- [x] Real RAG chain implemented (`ml/chains/qa_chain.py`)
- [x] Longitudinal Health Graph implemented in Neo4j (`ml/graph/`)
- [x] Unified visual document extraction via `datalab-to/lift` VLM with Option A RAG chunk synthesis
- [x] 220 unit tests passing (`ml/tests/`; run with `NEO4J_URI`/`NEO4J_PASSWORD` pointing at PHIRE's Neo4j)
- [x] Lift 4-bit NF4 quantization actually applied (`LiftExtractor._get_model`) and verified live on 8GB
- [x] Verifier fix: a clear entailing chunk beats contradictions from unrelated chunks
- [x] `QAChain.answer(on_progress=...)` stage callback

### Anika - Backend Infrastructure
- [x] Ollama + `medgemma:4b` running locally
- [x] `datalab-to/lift` VLM integrated via `ml_singletons`, run inside `gpu_mode(LIFT)`
- [x] PostgreSQL database setup with SQLAlchemy & Alembic migrations
- [x] FastAPI application with 8 routers & Pydantic models
- [x] HIPAA audit logging (dual PostgreSQL & append-only disk log)
- [x] GPU serialization + residency: `GPU_LOCK` wrapped by `gpu_mode(LIFT|CHAT)` (`app/services/gpu_modes.py`)
- [x] SSE progress endpoints (`POST /api/chat/stream`, `GET /api/documents/{id}/events`, `app/services/progress.py`)
- [x] Docker orchestration (`docker/docker-compose.yml`)

### Shashwati - Frontend & Evaluation
- [x] Next.js 16 project setup (App Router, React 19, TypeScript)
- [x] Patient Overview Dashboard with Recharts timeline (`frontend/app/page.tsx`)
- [x] Evidence-attributed medical chat interface (`frontend/app/chat/page.tsx`)
- [x] Document upload with live SSE ingestion progress (`frontend/app/documents/page.tsx`, `components/progress-steps.tsx`, `lib/sse.ts`)
- [x] Hybrid evidence search & claim verifier UI (`frontend/app/search/page.tsx`)
- [ ] Evaluation benchmark execution (ArchEHR-QA 2026 & MedHallBench)

---

## 🎯 Key Decisions Already Made

✅ **LLM & VLM**: Ollama + `medgemma:4b` (chat), `datalab-to/lift` (schema-guided visual document extraction)  
✅ **Vector DB**: Chroma (in-process)  
✅ **Graph DB**: Neo4j (Community Edition 5), queried directly via Cypher — for the Longitudinal Health Graph (structured patient facts, trend computation)  
✅ **Claim Verification**: NLI-based entailment/contradiction scoring (`facebook/bart-large-mnli`)  
✅ **Frontend**: Next.js 16, React 19, TailwindCSS, Recharts  
✅ **Backend**: FastAPI, SQLAlchemy, Alembic, PostgreSQL  
✅ **Privacy & Air-Gap**: Strict localhost enforcement via `ml.local_only.require_localhost()` and Docker host networking  

---

## 📊 What You're Building

### Core MVP
- Local healthcare AI that keeps data private
- Shows exactly where every medical claim comes from
- Understands your health trends (not just today's data)
- Refuses to guess when uncertain
- Ingests laboratory reports, PDFs, and medical scans

### Extended (9 months)
- Fitness & nutrition recommendation ML models
- Wearable integration (Fitbit, Oura, Apple Watch)
- Multi-hop graph-RAG retrieval (see `docs/GRAPH_SCHEMA_ROADMAP.md` §3f)
- 2 peer-reviewed papers published

---

## 📞 Quick Reference

| Question | Answer |
|----------|--------|
| What's the tech stack? | Next.js 16, FastAPI, Ollama, Chroma, Neo4j, PostgreSQL, Docker |
| Which LLM / VLM? | `medgemma:4b` (chat via Ollama), `datalab-to/lift` (schema-guided visual document extraction, 9.7B VLM) |
| How do I know what to do? | `docs/BACKLOG.md` and `docs/CODEBASE_AUDIT.md` have open items |
| What if I'm blocked? | Check `docs/API_REFERENCE.md` or `docs/FRONTEND_HANDOFF.md` |
