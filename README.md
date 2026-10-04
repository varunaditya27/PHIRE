# PHIRE: Personal Health Intelligence and Reasoning Engine

**Privacy-preserving, evidence-attributed healthcare AI powered by local LLMs**

PHIRE helps users understand their personal health data through an AI assistant that:
- Keeps all sensitive data local (no cloud, no data leakage)
- Traces every medical claim to exact evidence (lab values, document passages, calculations)
- Reasons over years of health history (detects trends, patterns, contradictions)
- Detects when it's uncertain and abstains (prevents false health information)

**Status**: Core ML pipeline (RAG, claim verification, Longitudinal Health Graph), FastAPI backend, and Next.js frontend are implemented and wired together. See [docs/FEATURES_ALIGNED.md](docs/FEATURES_ALIGNED.md) for feature alignment, [docs/CODEBASE_AUDIT.md](docs/CODEBASE_AUDIT.md) for the codebase audit, and [docs/BACKLOG.md](docs/BACKLOG.md) for known gaps.

---

## 🎯 What PHIRE Does

### Core Features (MVP)
- **Local LLM Chat**: Ask health questions without sending data to the cloud
- **Evidence Attribution**: Every answer traces atomic claims to verified records
- **Longitudinal Analysis**: Understands your health trends over time via graph modeling
- **Hallucination Detection**: Refuses to guess when evidence is insufficient
- **Document Processing**: Ingests lab reports, health records, and PDFs automatically

### Extended Features (Post-MVP)
- Fitness & nutrition recommendations with ML models
- Wearable data integration (Fitbit, Oura, Apple Watch)
- Multi-hop graph retrieval and contradiction detection
- Doctor-preparation summaries for clinical appointments
- FHIR-compliant health representations

---

## 🏗️ Architecture

```
Frontend (Next.js 16 + React 19)
    ↓
FastAPI Backend (Python 3.11+)
    ↓ ↙ ↘
Ollama               RAG System                      Neo4j Graph
(medgemma:4b)        (datalab-to/lift VLM +          (Longitudinal Health Graph:
                      MedCPT embeddings +             Observations, Timeline,
                      BM25 + Chroma +                 Medications, Conditions)
                      BART-large-MNLI)
    ↓
PostgreSQL (Upload Metadata, Chat History, Claims, Audit Logs)
```

RAG is hybrid, not vector-only: lexical (BM25) and semantic (Chroma) search
handle passage retrieval, while a local graph layer (Neo4j) stores structured
patient observations and precomputes trend deltas for arithmetic verification.

**Key design principle**: All data stays local. No cloud APIs, no external LLM calls.

---

## 🚀 Quick Start

### Requirements
- Python 3.11+, Node.js 20+
- 8GB RAM, GPU optional (NVIDIA GTX 3060+ recommended; CPU execution fully supported)
- Docker & Docker Compose
- ~20GB disk space (for models + data)

### Installation

```bash
# Clone repository
git clone https://github.com/varunaditya27/PHIRE.git
cd PHIRE

# Setup environment & dependencies
cp .env.example .env
bash scripts/setup.sh

# Start all services (PostgreSQL, Ollama, Neo4j, Backend, Frontend)
docker compose -f docker/docker-compose.yml up -d

# Verify system health
curl -X POST http://localhost:8000/api/health
```

### First Use

1. **Dashboard**: Navigate to `http://localhost:3000` to see your health overview.
2. **Upload Records**: Go to `http://localhost:3000/documents` and upload a PDF or scanned lab report.
3. **Ask Questions**: Open `http://localhost:3000/chat` and ask "What was my most recent LDL level?".
4. **Inspect Evidence**: Expand the Claim Verification audit trail to view exact confidence scores and source citations.

Both long waits show live progress over Server-Sent Events: uploads display each ingestion stage (loading the vision model, reading the document, indexing, saving to your timeline), and chat displays each pipeline stage (reading records, searching evidence, drafting, verifying claim *i* of *n*).

> If another app already uses port 3000, 7687 or 5433, run PHIRE on alternates — see [docs/BACKEND_HANDOFF.md §8.3](docs/BACKEND_HANDOFF.md).

---

### Start from scratch (clear demo/test data)

Before a real user ingests their own records, wipe everything left over from development:

```bash
PYTHONPATH=. ml/.venv/bin/python scripts/reset_data.py --dry-run   # show targets + counts, change nothing
PYTHONPATH=. ml/.venv/bin/python scripts/reset_data.py             # asks you to type RESET
```

It clears, using the targets in `backend/.env`: PostgreSQL (`documents`, `chat_messages`, `claims`, `audit_log`), the whole Neo4j health graph, **patient-document chunks** in Chroma, and uploaded files + the audit log file. Flags: `--keep-audit` (keep audit rows/file), `--include-reference` (also wipe the public reference corpus), `--yes` (skip the prompt). Restart the backend afterwards.

**Why the reference corpus is kept by default:** it is not user data. It is the public medical knowledge (MedlinePlus, PubMed abstracts, USDA nutrition) PHIRE retrieves from to ground general statements — without it a claim like "statins lower LDL" has nothing to be verified against and comes back unsupported, so answers could only restate the user's own records. It was ingested once with `ml/rag/ingest/run_ingest.py` (needs network); wiping it means re-running that.

## 📊 Features & Status

**Core**
- [x] Local LLM inference (Ollama, medgemma:4b)
- [x] Hybrid retrieval (BM25 + Chroma semantic search, MedCPT-reranked)
- [x] Evidence attribution (claim-level, with exact source citations)
- [x] Claim verification / hallucination detection (BART-large-MNLI, abstains below confidence threshold)
- [x] Longitudinal reasoning (Neo4j-backed patient fact graph: current state + trend deltas)
- [x] SSE live progress for document ingestion and chat (`GET /api/documents/{id}/events`, `POST /api/chat/stream`)
- [x] LIFT/CHAT GPU modes so lift and the chat models share an 8GB GPU by swapping (`backend/app/services/gpu_modes.py`)
- [x] Document ingestion (unified single-pass visual extraction via `datalab-to/lift` 9.7B VLM with 4-bit NF4 on CUDA applied in `LiftExtractor`, ~6.5GiB peak on an 8GB GPU, and CPU fallback)
- [x] Backend API integration (FastAPI with 8 routers, HIPAA audit logging, GPU lock)
- [x] Frontend UI (Next.js 16 App Router: Dashboard, Chat, Documents, Search)

**Extended (post-core)**
- [ ] Fitness recommendations (HAR model)
- [ ] Nutrition recommendations (meal planner)
- [ ] Wearable integration
- [ ] Multi-hop graph-RAG retrieval
- [ ] FHIR-compliant representation

See [docs/FEATURES_ALIGNED.md](docs/FEATURES_ALIGNED.md) for the complete feature checklist.

---

## 🛠️ Tech Stack

- **Frontend**: Next.js 16, React 19, TypeScript, TailwindCSS, Lucide Icons, Recharts
- **Backend**: FastAPI, Python 3.11+, SQLAlchemy, Alembic, PostgreSQL
- **LLM & VLM**: Ollama (`medgemma:4b` for chat), `datalab-to/lift` (9.7B parameter schema-guided VLM for single-pass visual document extraction)
- **Embeddings / Reranking**: `ncbi/MedCPT` (dual encoder + cross-encoder)
- **Claim verification**: `facebook/bart-large-mnli` (NLI entailment/contradiction scoring)
- **Vector DB**: Chroma (in-process)
- **Graph DB**: Neo4j (Community Edition 5), queried directly via Cypher
- **Deployment**: Docker, Docker Compose (host networking for local privacy compliance)

---

## 📖 Documentation

- **[docs/CODEBASE_AUDIT.md](docs/CODEBASE_AUDIT.md)** - Comprehensive master audit of features, inconsistencies, bugs, and design decisions
- **[docs/BACKLOG.md](docs/BACKLOG.md)** - Known gaps, tech debt, and open design questions across all subsystems
- **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** - Full request/response reference for every backend endpoint
- **[docs/FRONTEND_HANDOFF.md](docs/FRONTEND_HANDOFF.md)** - Frontend UI architecture, page inventory, and active tasks
- **[docs/BACKEND_HANDOFF.md](docs/BACKEND_HANDOFF.md)** - Backend integration history, verification tests, and architecture
- **[docs/FEATURES_ALIGNED.md](docs/FEATURES_ALIGNED.md)** - Complete feature roadmap aligned to NLP-06 specifications
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Roles, work division, detailed task breakdown
- **[GET_STARTED.md](GET_STARTED.md)** - First-day setup & onboarding checklist
- **[ml/README.md](ml/README.md)** - `ml/` subsystem architecture, benchmarks, and model selection
- **[backend/README.md](backend/README.md)** - `backend/` subsystem configuration and quick start
- **[REPO_STRUCTURE.md](REPO_STRUCTURE.md)** - Repository layout & folder ownership

---

## 🔬 Research & Publication

**Research Questions**:
1. Can claim-level evidence attribution reduce hallucinations in local healthcare LLMs?
2. Does structured temporal representation improve trend reasoning accuracy?
3. Can explicit verification reduce unsupported medical claims by 40%+?
4. What privacy-utility trade-offs emerge at 7B vs 70B model scale?

**Publication Timeline**:
- Paper 1 (Month 4): Evidence attribution + longitudinal reasoning
- Paper 2 (Month 8): Hallucination detection + privacy-utility trade-offs
- Target venues: ACL, EMNLP, NeurIPS, Medical AI conferences

---

## 🤝 Contributing

PHIRE is built by a 3-person team with parallel workstreams:
- **Varun**: ML & Intelligence (RAG, claims, evidence attribution, recommendations)
- **Anika**: Backend Infrastructure (FastAPI, Ollama, PostgreSQL, Chroma, Docker)
- **Shashwati**: Frontend & Evaluation (Next.js UI, metrics, benchmarks, research)

---

## ⚠️ Disclaimer

**PHIRE is NOT a medical device and NOT a substitute for professional medical advice.**

PHIRE is designed for **wellness and decision-support** purposes only:
- ✅ Help you understand your health data
- ✅ Prepare questions for your doctor
- ✅ Track trends in your health metrics
- ❌ NOT for diagnosis or treatment decisions
- ❌ NOT a replacement for talking to healthcare professionals
- ❌ NOT for medical emergencies (call 911 or your doctor)

---

## 📚 Citation

```bibtex
@software{phire2026,
  title={PHIRE: Privacy-Preserving Local Healthcare AI with Evidence Attribution},
  author={Aditya, Varun and Bhat, Anika U and Rao, M. Shashwati},
  year={2026},
  url={https://github.com/varunaditya27/PHIRE}
}
```
