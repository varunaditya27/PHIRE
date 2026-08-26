# PHIRE: Personal Health Intelligence and Reasoning Engine

**Privacy-preserving, evidence-attributed healthcare AI powered by local LLMs**

PHIRE helps users understand their personal health data through an AI assistant that:
- Keeps all sensitive data local (no cloud, no data leakage)
- Traces every medical claim to exact evidence (lab values, document passages, calculations)
- Reasons over years of health history (detects trends, patterns, contradictions)
- Detects when it's uncertain and abstains (prevents false health information)

**Status**: Core ML pipeline (RAG, claim verification, Longitudinal Health Graph) implemented and live-tested; backend/frontend integration and extended features in progress. See [docs/FEATURES_ALIGNED.md](docs/FEATURES_ALIGNED.md) for the current checklist.

---

## 🎯 What PHIRE Does

### Core Features (MVP)
- **Local LLM Chat**: Ask health questions without sending data to cloud
- **Evidence Attribution**: Every answer shows exactly where information comes from
- **Longitudinal Analysis**: Understands your health trends over years, not just today
- **Hallucination Detection**: Refuses to guess when evidence is insufficient
- **Document Processing**: Ingests lab reports, health records, PDFs automatically

### Extended Features (Post-MVP)
- Fitness & nutrition recommendations with ML models
- Wearable data integration (Fitbit, Oura, Apple Watch)
- Contradiction detection (alerts when records conflict)
- Doctor-preparation summaries for clinical appointments
- FHIR-compliant health representations

---

## 🏗️ Architecture

```
Frontend (Next.js)
    ↓
FastAPI Backend (Python)
    ↓ ↙ ↘
Ollama     RAG System            ML Models
(Local     (Chroma vector +      (Recommendations —
 LLM)       BM25 + Neo4j graph)   not yet built)
    ↓ ↓ ↓ ↓
PostgreSQL (Patient Data, Timeline, Claims, Evidence)
```

RAG is hybrid, not vector-only: lexical (BM25) and semantic (Chroma) search
handle single-hop lookups; a graph layer (Neo4j, queried directly via
Cypher — LightRAG was evaluated and not adopted, see
[docs/DATASETS_AND_GRAPH_RAG.md](docs/DATASETS_AND_GRAPH_RAG.md)) handles
longitudinal patient facts and trend computation today, with multi-hop
graph-RAG retrieval as future work (see
[docs/GRAPH_SCHEMA_ROADMAP.md](docs/GRAPH_SCHEMA_ROADMAP.md)).

**Key design principle**: All data stays local. No cloud APIs, no external LLM calls.

---

## 🚀 Quick Start

### Requirements
- Python 3.10+, Node.js 18+
- 8GB RAM, GPU optional (NVIDIA GTX 3060+ recommended)
- Docker & Docker Compose
- ~20GB disk space (for models + data)

### Installation

```bash
# Clone repository
git clone https://github.com/varunaditya27/PHIRE.git
cd PHIRE

# Setup environment
cp .env.example .env
bash scripts/setup.sh

# Start all services (Ollama, FastAPI, Next.js, PostgreSQL, Chroma)
docker-compose up -d

# Check services running
curl http://localhost:8000/health
```

### First Use

1. **Upload health data**: Upload a PDF lab report via the UI
2. **Ask a question**: "What's my latest LDL level?"
3. **See evidence**: Click on the answer to see exact source highlighted
4. **Build timeline**: System automatically creates your health timeline

---

## 📊 Features & Status

**Core**
- [x] Local LLM inference (Ollama, medgemma:4b)
- [x] Hybrid retrieval (BM25 + Chroma semantic search, MedCPT-reranked)
- [x] Evidence attribution (claim-level, with exact source spans)
- [x] Claim verification / hallucination detection (NLI-based, abstains below confidence threshold)
- [x] Longitudinal reasoning (Neo4j-backed patient fact graph: current state + trend deltas)
- [x] Document ingestion (text PDFs + scanned/photographed documents via OCR)
- [ ] Backend API integration (`backend/` wiring to `ml/`)
- [ ] Frontend chat UI

**Extended (post-core)**
- [ ] Fitness recommendations
- [ ] Nutrition recommendations
- [ ] Wearable integration
- [ ] Multi-hop graph-RAG retrieval (LightRAG-style, beyond today's single-patient fact lookups)
- [ ] FHIR-compliant representation

See [docs/FEATURES_ALIGNED.md](docs/FEATURES_ALIGNED.md) for the complete feature checklist.

---

## 🛠️ Tech Stack

- **Frontend**: Next.js 14, React, TypeScript
- **Backend**: FastAPI, Python 3.10+
- **LLM**: Ollama + medgemma:4b (chat), qwen3.5:9b (prose fact extraction), olmOCR-v2 (scanned/photographed document OCR) — all benchmarked, see `ml/*/experiments/RESULTS.md`
- **Embeddings / Reranking**: MedCPT (dual encoder + cross-encoder)
- **Claim verification**: BART-large-MNLI (NLI-based entailment/contradiction scoring)
- **Vector DB**: Chroma (in-process)
- **Graph DB**: Neo4j (Community Edition), queried directly via Cypher — for the Longitudinal Health Graph (structured patient facts, trend computation)
- **Database**: PostgreSQL
- **ML Models**: PyTorch (transformers) for RAG/claims; recommendation models not yet built
- **Deployment**: Docker, Docker Compose

---

## 📖 Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Roles, work division, detailed task breakdown
- **[GET_STARTED.md](GET_STARTED.md)** - First-day setup & onboarding checklist
- **[ml/README.md](ml/README.md)** - `ml/` subsystem: architecture, quick start, model choices, feature status
- **[docs/FEATURES_ALIGNED.md](docs/FEATURES_ALIGNED.md)** - Complete feature roadmap (MVP + extended, aligned to NLP-06)
- **[docs/AGGRESSIVE_ROADMAP.md](docs/AGGRESSIVE_ROADMAP.md)** - Build checklist: core MVP + extended features
- **[docs/OPEN_SOURCE_TOOLS.md](docs/OPEN_SOURCE_TOOLS.md)** - 40+ open-source tools & integration guide
- **[docs/DATASETS_AND_GRAPH_RAG.md](docs/DATASETS_AND_GRAPH_RAG.md)** - Finalized fitness/nutrition datasets, model choices, and the hybrid vector + graph RAG architecture
- **[REPO_STRUCTURE.md](REPO_STRUCTURE.md)** - Repository layout & folder ownership

---

## 🔬 Research & Publication

**Research Questions** (addressed by this project):
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

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Work division & roles
- How to contribute (bug fixes, features, research)
- Pull request process

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

Always consult qualified healthcare professionals for medical decisions. PHIRE is a research project and educational tool.

---

## 📋 Research Basis

Every feature in PHIRE is backed by peer-reviewed research (2023-2026):
- **Evidence attribution / claim verification**: NLI-based entailment/contradiction scoring (BART-large-MNLI, selected via a 129-pair benchmark against 5 other candidates including medical-specialized models — see `ml/claims/experiments/RESULTS.md`); MedRAGChecker was evaluated during tool selection but isn't installable/integrated, see `docs/OPEN_SOURCE_TOOLS.md`
- **Temporal reasoning**: Longitudinal health reasoning (multiple 2025 papers)
- **Hallucination detection**: MedHallBench (2025)
- **Local model deployment**: Privacy-preserving LLM studies (2024-2026)
- **Evaluation**: ArchEHR-QA benchmark (2026)


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

---

## 📞 Questions?

- **Setup issues**: Check [GET_STARTED.md](GET_STARTED.md)
- **How to contribute**: See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Feature questions**: See [docs/FEATURES_ALIGNED.md](docs/FEATURES_ALIGNED.md)

---

**Built with 🔬 research rigor, 🏥 healthcare focus, 🔒 privacy-first design**

Last updated: 2026-08-26
