# PHIRE: Personal Health Intelligence and Reasoning Engine

**Privacy-preserving, evidence-attributed healthcare AI powered by local LLMs**

PHIRE helps users understand their personal health data through an AI assistant that:
- Keeps all sensitive data local (no cloud, no data leakage)
- Traces every medical claim to exact evidence (lab values, document passages, calculations)
- Reasons over years of health history (detects trends, patterns, contradictions)
- Detects when it's uncertain and abstains (prevents false health information)

**Status**: MVP in development (3-week sprint) + 9-month research roadmap

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
Ollama     RAG System      ML Models
(Local     (Chroma)        (Recommendations)
 LLM)
    ↓ ↓ ↓ ↓
PostgreSQL (Patient Data, Timeline, Claims, Evidence)
```

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
git clone https://github.com/varunaditya/PHIRE.git
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

| Feature | Status | Timeline |
|---------|--------|----------|
| Local LLM inference | ✅ MVP | Week 1 |
| Evidence attribution | ✅ MVP | Week 2-3 |
| Longitudinal reasoning | ✅ MVP | Week 1-2 |
| Hallucination detection | ✅ MVP | Week 3 |
| Document ingestion | ✅ MVP | Week 1 |
| Fitness recommendations | 🔄 Extended | Month 4-6 |
| Nutrition recommendations | 🔄 Extended | Month 4-6 |
| Wearable integration | 🔄 Extended | Month 7-9 |
| Contradiction detection | 🔄 Extended | Month 4-6 |
| FHIR representation | 🔄 Extended | Month 6-8 |

See [docs/FEATURES_ALIGNED.md](docs/FEATURES_ALIGNED.md) for complete feature roadmap.

---

## 🛠️ Tech Stack

- **Frontend**: Next.js 14, React, TypeScript
- **Backend**: FastAPI, Python 3.10+
- **LLM**: Ollama + MedGemma 1.5 8B (or Meditron-7B)
- **Vector DB**: Chroma (or Qdrant)
- **Database**: PostgreSQL
- **ML Models**: TensorFlow/PyTorch (optional, for recommendations)
- **Deployment**: Docker, Docker Compose

---

## 📖 Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Roles, work division, detailed task breakdown
- **[GET_STARTED.md](GET_STARTED.md)** - First-day setup & onboarding checklist
- **[docs/FEATURES_ALIGNED.md](docs/FEATURES_ALIGNED.md)** - Complete feature roadmap (MVP + extended, aligned to NLP-06)
- **[docs/AGGRESSIVE_ROADMAP.md](docs/AGGRESSIVE_ROADMAP.md)** - 3-week MVP + 9-month timeline
- **[docs/OPEN_SOURCE_TOOLS.md](docs/OPEN_SOURCE_TOOLS.md)** - 40+ open-source tools & integration guide
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
- **Evidence attribution**: MedRAGChecker (2025)
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
  url={https://github.com/varunaditya/phire}
}
```

---

## 📞 Questions?

- **Setup issues**: Check [GET_STARTED.md](GET_STARTED.md)
- **How to contribute**: See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Feature questions**: See [docs/FEATURES_ALIGNED.md](docs/FEATURES_ALIGNED.md)

---

**Built with 🔬 research rigor, 🏥 healthcare focus, 🔒 privacy-first design**

Last updated: August 2026
