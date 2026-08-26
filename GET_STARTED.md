# PHIRE: Ready to Code - Get Started NOW

**Status**: ✅ Research complete, cleanup complete, documentation ready
**Date**: August 15, 2026
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

### 3. **docs/AGGRESSIVE_ROADMAP.md** (15 min)
- Core build checklist
- Extended roadmap phases
- Success metrics

### 4. **docs/FEATURES_ALIGNED.md** (5 min, reference)
- Complete feature list (Tier 1-4)
- What's in MVP vs. extended


---

## 🚀 TODAY: Setup & Kickoff

### This Morning (30 min)
```bash
# All three team members:
1. Read README.md + CONTRIBUTING.md sections for your role
2. Create GitHub Issues for Week 1 tasks (from CONTRIBUTING.md)
3. Setup GitHub Project board (Week 1, Week 2, Week 3 columns)
```

### This Afternoon (1 hour)
```bash
# Varun (ML) — see ml/requirements.txt for the full pinned list, uv-managed:
$ pip install transformers sentence-transformers torch chromadb rank_bm25 neo4j
# Embedding/reranking models (MedCPT) and the NLI verifier (BART-large-MNLI)
# download automatically on first use via ml/rag/embeddings.py, ml/rag/reranker.py,
# ml/claims/verifier.py — no separate manual download step.

# Anika (Backend):
$ curl -fsSL https://ollama.ai/install.sh | sh
$ ollama pull medgemma:4b   # chat generation, ~2.5GB
$ ollama pull qwen3.5:9b    # prose fact extraction (ml/graph/prose_extraction.py)
$ pip install fastapi uvicorn sqlalchemy psycopg2
$ docker --version && docker-compose --version
# Neo4j (Longitudinal Health Graph — required for ml/graph/, see ml/.env.example):
$ podman run -d --name phire-neo4j -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/<password> -v phire-neo4j-data:/data \
    docker.io/library/neo4j:5-community

# Shashwati (Frontend):
$ node --version && npm --version
$ pip install pandas numpy scikit-learn scipy matplotlib seaborn
# Download ArchEHR-QA benchmark (link in CONTRIBUTING.md)
```

### Late Afternoon (1 hour)
```bash
# All three:
$ git clone https://github.com/varunaditya27/PHIRE.git
$ cd PHIRE

# Create feature branch for Week 1 work
$ git checkout -b feat/week1-infrastructure
$ git checkout -b feat/week1-evidence-rag
$ git checkout -b feat/week1-evaluation
```

### 5 PM: Team Meeting (30 min)
- **Confirm**: Tech stack decisions (Ollama ✅, Chroma ✅, medgemma:4b ✅, Neo4j ✅)
- **Confirm**: Model choices — see `ml/*/experiments/RESULTS.md` for the benchmarks behind each (medgemma:4b for chat, qwen3.5:9b for prose extraction, MedCPT for embeddings/reranking, BART-large-MNLI for claim verification, olmOCR-v2 for OCR)
- **Setup**: Daily standup time (9 AM)
- **Setup**: Weekly sync time (Friday 3 PM)
- **Divide**: Issue assignments (Week 1 tasks from CONTRIBUTING.md)

---

## 📅 WEEK 1 TASKS (From CONTRIBUTING.md)

### Varun's Week 1 - ML & Intelligence — all done, see CONTRIBUTING.md
- [x] Download embedding model (medical-specialized) — MedCPT
- [x] Setup Chroma vector DB (native Python)
- [x] Ingest 50+ clinical reference documents
- [x] Design LLM prompt for claim extraction (v1)
- [x] Design claim verification approach — NLI-based (BART-large-MNLI), not MedRAGChecker (not installable)
- [x] Real RAG chain implemented (`ml/chains/qa_chain.py`)

### Anika's Week 1 - Backend Infrastructure
- [ ] Ollama + medgemma:4b running locally
- [ ] PostgreSQL Docker setup (Chroma is the vector store, not pgvector)
- [ ] FastAPI project scaffold + basic endpoints
- [ ] Database schema + migrations
- [ ] docker-compose file for all services

### Shashwati's Week 1 - Frontend & Evaluation
- [ ] Next.js 15 project setup (app router, TypeScript)
- [ ] Chat component scaffold (input + response display)
- [ ] Tailwind CSS + responsive layout
- [ ] Create 10 evaluation questions with expert answers
- [ ] Download ArchEHR-QA 2026 dataset
- [ ] Design evaluation metrics (precision, recall, F1)

**Week 1 Deliverable**: All three components working independently, ready for integration Week 2

---

## 🎯 Key Decisions Already Made

✅ **LLM**: Ollama + medgemma:4b (chat), qwen3.5:9b (prose fact extraction) — MedGemma ships only as 4B/27B, not "1.5"/"8B"
✅ **Vector DB**: Chroma native Python (in-process)
✅ **Graph DB**: Neo4j, queried directly via Cypher — for the Longitudinal Health Graph (structured patient facts, trend computation); LightRAG was evaluated and is **not yet implemented** — multi-hop graph-RAG retrieval is still outstanding work, see `docs/GRAPH_SCHEMA_ROADMAP.md`
✅ **Claim Verification**: NLI-based entailment/contradiction scoring (BART-large-MNLI) — not MedRAGChecker, which isn't installable (see `docs/OPEN_SOURCE_TOOLS.md`)
✅ **ML**: Pre-trained HAR (fitness) planned but not yet started; nutrition model not yet started
✅ **Frontend**: Next.js 15 (server components keep PHI server-side)
✅ **Backend**: FastAPI (type-safe, async, production-ready)
✅ **Database**: PostgreSQL (relational only — patients, timeline, claims, evidence), Chroma is the vector store
✅ **Evaluation**: ArchEHR-QA 2026 (167 expert cases, modular assessment)

---

## 📊 What You're Building

### MVP (3 weeks)
- Local healthcare AI that keeps data private
- Shows exactly where every medical claim comes from
- Understands your health trends (not just today's data)
- Refuses to guess when uncertain
- Gives fitness recommendations

### Extended (9 months)
- Nutrition recommendations (ML model trained on real data)
- Wearable integration (Fitbit, Oura, Apple Watch)
- Multi-hop graph-RAG retrieval (see `docs/GRAPH_SCHEMA_ROADMAP.md` §3f)
- 2 peer-reviewed papers published

PHIRE is a single-user, local-only personal health tool — one instance
per person, not a multi-tenant clinical system. "Multi-region healthcare
network deployment" and an "FDA 510(k) regulatory pathway" were removed
from this list (2026-08-26): both describe a different product category
(a multi-patient clinical device requiring regulatory clearance), not
this project's scope.

---

## ⚡ AI Agent Strategy

**Use agents for**:
- Boilerplate code generation
- Test case generation
- Documentation
- Docker/CI-CD automation

**Don't use agents for** (human domain):
- Architecture decisions
- Research methodology
- Safety/security design
- Paper core ideas

---

## 🚨 Critical Path (Don't Get Blocked)

**Week 1**: All three work independently (no blocking)
- Varun builds ML/RAG (doesn't need Anika's backend yet, uses mocks)
- Anika builds backend/frontend (doesn't need Varun's RAG yet)
- Shashwati creates evaluation framework (doesn't need live system)

**Week 2**: Start integration
- Anika provides `/api/observations` endpoint
- Varun connects RAG to Anika's backend
- Shashwati runs baseline evaluation

**Week 3**: Final integration + polish
- All three subsystems connected
- Evaluation shows results
- Demo-ready

**Key principle**: If blocked, find async path (mock data, dummy responses, etc.)

---

## ✅ Pre-Flight Checklist

Before starting Week 1:
- [ ] All three read README.md
- [ ] All three read CONTRIBUTING.md (your role section)
- [ ] Varun: Embedding model downloaded, Chroma installed
- [ ] Anika: Ollama installed, MedGemma downloaded, Docker ready
- [ ] Shashwati: ArchEHR-QA downloaded, metrics designed
- [ ] GitHub repo created, all three are collaborators
- [ ] GitHub Project board created (Week 1, 2, 3 columns)
- [ ] Week 1 Issues created and assigned
- [ ] Daily standup scheduled (9 AM)
- [ ] Weekly sync scheduled (Friday 3 PM)
- [ ] Slack/Discord channel created for team
- [ ] Everyone has access to shared resources (no permission issues)

---

## 🎓 Expected Outcomes

### Core MVP
- Working personal health AI demo (3 realistic individual-user personas — not clinician personas; PHIRE is single-user, not clinician-facing)
- Evidence attribution system (claims → sources)
- Hallucination detection working
- Fitness recommendations active
- Evaluation metrics quantified
- GitHub repo ready for public
- Deployment automated (docker-compose up -d)

### Extended
- Nutrition ML model trained
- Wearable integration working
- 2 research papers published (ACL/EMNLP)
- Open-source release with benchmark
- Multi-hop graph-RAG retrieval built (see `docs/GRAPH_SCHEMA_ROADMAP.md` §3f)

"Healthcare network pilot deployment" and "FDA 510(k) pathway mapped"
removed (2026-08-26) — PHIRE is a single-user, local-only personal health
tool, not a multi-tenant clinical system; that's a different product
category, not this project's extended scope.

---

## 📞 Quick Reference

| Question | Answer |
|----------|--------|
| What's the tech stack? | Next.js, FastAPI, Ollama, Chroma, Neo4j, PostgreSQL, Docker |
| Which LLM? | medgemma:4b (chat), qwen3.5:9b (prose fact extraction) — see `ml/*/experiments/RESULTS.md` for why |
| How do I know what to do? | CONTRIBUTING.md has your detailed role + tasks |
| What if I'm blocked? | Daily standup at 9 AM to unblock immediately |
| Can I use AI coding agents? | Yes, for boilerplate, test generation, docs |
| Do I need to know all the research? | No, just your subsystem. `docs/RESEARCH_LOG.md` (ml/) has dated findings/decisions if you want the "why" |

---

## 🚀 LET'S GO

You have:
✅ Clear requirements (docs/AGGRESSIVE_ROADMAP.md)
✅ Clear roles (CONTRIBUTING.md)
✅ Clear tech stack (README.md + decisions above)
✅ Clear evaluation (ArchEHR-QA 2026)
✅ Clear timeline (3 weeks MVP, 9 months extended)
✅ No unknowns (2023-2026 research foundation)

**What's left**: Code it.

**Start now**: Setup tasks above (30 min), Week 1 kickoff tomorrow.

The competitive window is 6-12 months. Move fast.

---

**Questions?**
- Setup issues → See README.md
- Role clarity → See CONTRIBUTING.md
- Feature details → See docs/FEATURES_ALIGNED.md or docs/AGGRESSIVE_ROADMAP.md
- Daily decisions → Daily standup, weekly sync

**Status**: 🟢 READY TO START

Let's build PHIRE. 🚀
