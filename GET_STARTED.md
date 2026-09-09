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
cp .env.example .env
bash scripts/setup.sh
docker compose -f docker/docker-compose.yml up -d
curl -X POST http://localhost:8000/api/health
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
- [x] Design LLM prompt for claim extraction (`medgemma:4b` / `qwen3.5:9b`)
- [x] Design claim verification approach — NLI-based (`facebook/bart-large-mnli`)
- [x] Real RAG chain implemented (`ml/chains/qa_chain.py`)
- [x] Longitudinal Health Graph implemented in Neo4j (`ml/graph/`)
- [x] 189 unit & integration tests passing (`ml/tests/`)

### Anika - Backend Infrastructure
- [x] Ollama + models (`medgemma:4b`, `qwen3.5:9b`, `olmOCR-2-7B`) running locally
- [x] PostgreSQL database setup with SQLAlchemy & Alembic migrations
- [x] FastAPI application with 8 routers & Pydantic models
- [x] HIPAA audit logging (dual PostgreSQL & append-only disk log)
- [x] GPU serialization lock (`GPU_LOCK`)
- [x] Docker orchestration (`docker/docker-compose.yml`)

### Shashwati - Frontend & Evaluation
- [x] Next.js 16 project setup (App Router, React 19, TypeScript)
- [x] Patient Overview Dashboard with Recharts timeline (`frontend/app/page.tsx`)
- [x] Evidence-attributed medical chat interface (`frontend/app/chat/page.tsx`)
- [x] Document upload & polling ingestion UI (`frontend/app/documents/page.tsx`)
- [x] Hybrid evidence search & claim verifier UI (`frontend/app/search/page.tsx`)
- [ ] Evaluation benchmark execution (ArchEHR-QA 2026 & MedHallBench)

---

## 🎯 Key Decisions Already Made

✅ **LLM**: Ollama + `medgemma:4b` (chat), `qwen3.5:9b` (prose fact extraction), `olmOCR-2-7B` (OCR)  
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
| Which LLM? | `medgemma:4b` (chat), `qwen3.5:9b` (prose fact extraction), `olmOCR-2-7B` (OCR) |
| How do I know what to do? | `docs/BACKLOG.md` and `docs/CODEBASE_AUDIT.md` have open items |
| What if I'm blocked? | Check `docs/API_REFERENCE.md` or `docs/FRONTEND_HANDOFF.md` |
