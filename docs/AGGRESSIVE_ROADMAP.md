# PHIRE: Implementation Roadmap
## Core Build Checklist + Extended Phases

**Team**: Varun (ML & Intelligence), Anika (Backend Infrastructure), Shashwati (Frontend & Evaluation)
**Research Basis**: 2023-2026 healthcare AI evolution analysis

**Note (2026-08-26)**: this doc originally used a 3-week/9-month calendar
framing with hour-based effort estimates. Both removed — the checklists
below reflect actual build status, not a schedule or a time budget.

---

## 🚀 Core Build Checklist

### Infrastructure Bootstrap
- [x] Ollama + medgemma:4b (chat), qwen3.5:9b (prose extraction) → localhost:11434
- [x] PostgreSQL (Docker) — Chroma is the vector store, not pgvector
- [x] Chroma vector DB (native Python, in-process)
- [x] Neo4j (Docker/podman) — Longitudinal Health Graph
- [x] FastAPI scaffold with async routing — all 8 routers wired to real `ml/` interfaces, not stubs (`backend/README.md`)
- [ ] Next.js 15 setup with server components (keeps PHI server-side) — repo scaffolded (`create-next-app`), no app code written yet
- **Deliverable**: All services running, basic API endpoints — ✅ true for `ml/` + `backend/` (live-tested end-to-end, see `docs/BACKEND_HANDOFF.md`); frontend scaffolding exists but is unmodified boilerplate

### Document Pipeline + RAG Core
- [x] PDF/OCR extraction (pypdf + olmOCR-v2, not Docling) → normalized observations
- [x] Chroma ingestion pipeline (embed clinical reference docs — PubMed, MedlinePlus, USDA)
- [x] BM25 lexical retrieval (exact term matching for lab values)
- [x] Hand-written RAG chain with Ollama (`ml/chains/qa_chain.py`) — LangChain evaluated, not adopted
- [x] Backend retrieval endpoint: `/api/evidence/retrieve` (`GET /api/search/evidence` too — see `docs/API_REFERENCE.md`)
- **Deliverable**: Query "LDL" → returns relevant evidence — ✅ done and exposed via backend (`docs/API_REFERENCE.md`'s Evidence & Claims section)

### Claim Extraction + Verification
- [x] LLM prompt for structured claim extraction (atomic facts)
- [x] NLI-based claim verification (BART-large-MNLI, `ml/claims/verifier.py`) — not MedRAGChecker, which isn't installable
- [x] Confidence scoring (status taxonomy: SUPPORTED, DERIVED, CONFLICTING, UNCERTAIN, UNSUPPORTED — not INFERRED, no validated signal for it yet)
- [x] Entailment checking (does evidence support claim?)
- [ ] UI: Chat interface + clickable evidence highlights
- **Deliverable**: `/api/chat` returns claims with evidence links — ✅ done and exposed via `POST /api/chat` (`docs/API_REFERENCE.md`); not yet rendered in a UI

### Longitudinal Reasoning
- [x] Health timeline construction (Observations grouped by date, Neo4j)
- [x] Temporal normalization (day-first date parsing, DOB exclusion — `ml/graph/document_dates.py`)
- [x] Trend detection (latest vs. previous reading, `ml/graph/patient_context.py`'s `get_trend_facts`)
- [x] LLM reasoning over timeline context
- [x] Enhanced prompt: patient context + evidence + trend facts
- **Deliverable**: System understands "your LDL has increased 18 points" — ✅ done and live-tested (labeled `DERIVED`, not asserted by the LLM itself)

### Fitness Recommendations + Hallucination Detection
- [ ] Pre-trained HAR model (PAMAP2-based, activity recognition) — not started
- [ ] Fitness recommendation engine — not started (`ml/recommendations/` is stubs only)
- [x] Unsupported claim detection (flag claims without evidence)
- [x] Abstention logic (refuse to answer if uncertain)
- [ ] Safety gates for high-risk claims (medications, diagnoses) — beyond the general abstention threshold, no dedicated high-risk gate yet
- **Deliverable**: System gives fitness advice + halts on unsupported health claims — hallucination detection ✅ done and live-tested; fitness advice ❌ not started

### Integration + Polish
- [ ] Connect all subsystems (frontend ↔ backend ↔ RAG ↔ LLM ↔ HAR) — `backend` ↔ `ml/` wired and live-tested (`docs/BACKEND_HANDOFF.md`); `frontend` ↔ `backend` not started (see `docs/FRONTEND_HANDOFF.md`)
- [x] Error handling, logging, HIPAA audit trails (backend scope) — `AuditMiddleware` (`backend/app/security.py`), per-request audit log
- [ ] Caching layer (reduce LLM inference latency)
- [x] Privacy audit within `ml/` — every Ollama/Neo4j call enforces local-only at the code level (`ml/local_only.py`), not just convention
- **Deliverable**: Complete end-to-end system working — ✅ true for `ml/` + `backend/` together (live-tested, including a full review pass — see `CHANGELOG.md`'s `[0.5.0]`); not yet true end-to-end through a UI. See `docs/BACKLOG.md` for what's still open in ml/backend before that.

### Evaluation + Documentation
- [ ] ArchEHR-QA 2026 evaluation (167 expert cases) — not started (Shashwati's scope)
- [ ] Baseline metrics: evidence attribution precision/recall, claim extraction quality, hallucination rate, response latency
- [x] Live end-to-end pipeline testing (`ml/tests/test_qa_chain_live_e2e.py`, real Ollama/Neo4j/Chroma, no mocks)
- [ ] Demo personas + end-to-end workflow testing through a UI
- [x] README + deployment guide — `ml/README.md`, `backend/README.md` done; frontend's still pending its own build
- [ ] CI/CD setup

---

## 📊 Core Feature Status

| Feature | Status | Research Value |
|---------|--------|-----------------|
| Local LLM inference | ✅ | Baseline |
| Evidence attribution | ✅ (ml/ pipeline; UI not built) | ⭐⭐⭐⭐⭐ |
| Longitudinal reasoning | ✅ | ⭐⭐⭐⭐⭐ |
| Hallucination detection | ✅ | ⭐⭐⭐⭐ |
| Document ingestion | ✅ | ⭐⭐ |
| Fitness recommendations | ❌ not started | ⭐⭐⭐⭐ |
| Health timeline (graph) | ✅ (ml/ facts + trends; visualization not built) | ⭐⭐⭐⭐ |
| ArchEHR-QA evaluation | ❌ not started | ⭐⭐⭐⭐ |

---

## 🎯 Extended Roadmap (Phased, Not Calendar-Bound)

### Phase 2: Advanced Evidence & ML
- [ ] Contradiction detection (conflicting lab values across visits) — see `docs/GRAPH_SCHEMA_ROADMAP.md` §3b (claim→evidence graph edges) for the prerequisite groundwork
- [ ] Evidence ranking beyond current authority/recency (guidelines > RCTs > observational data)
- [ ] Multi-modal document understanding (images + tables + text)
- [ ] Start nutrition recommendation data collection
- [ ] Privacy-utility benchmark (local vs. cloud models)

### Phase 3: ML Models & Personalization
- [ ] Nutrition recommendation model training
- [ ] Fitness recommendation model (HAR fine-tuning, wearable integration)
- [ ] Advanced temporal reasoning (trajectory prediction, anomaly detection)
- [ ] Multi-disease interaction modeling

### Phase 4: Multimodal + Multi-hop Retrieval
- [ ] Multi-hop graph-RAG retrieval (LightRAG-style entity/relationship traversal) — **not yet implemented, outstanding work**, see `docs/GRAPH_SCHEMA_ROADMAP.md` §3f
- [ ] Medical image understanding (X-rays, lab graphs)
- [ ] Structured + unstructured data fusion
- [ ] Explainability improvements (show reasoning)

### Phase 5: Hardening & Research
- [ ] Advanced audit logging (local, single-user — see below)
- [ ] Paper 1: Evidence attribution + longitudinal reasoning
- [ ] Paper 2: Hallucination detection + privacy-utility
- [ ] Reproducible artifacts (code + benchmark + datasets), open-source release

**Note (2026-08-26)**: this phase previously listed "multi-region setup
(hospital networks)," "role-based access control (clinician vs.
patient)," and an FDA 510(k) regulatory pathway. Removed — PHIRE is a
**single-user, single-instance, local-only personal health tool**, not a
multi-tenant clinical system (see `CLAUDE.md`'s "wellness/decision-support
tool, not a medical device" framing and `docs/GRAPH_SCHEMA_ROADMAP.md`'s
"single-user-per-local-instance model, not a multi-tenant assumption" —
both stated as permanent architecture, not just current MVP scope).
Multi-tenant/RBAC/regulatory-clearance work is a different product
category and out of scope, not a later phase of this one.

---

## 🎯 Success Metrics (Core Scope)

### Technical Success
- [ ] Response latency <3 seconds end-to-end (ml/ pipeline latency not yet benchmarked outside live-test runs)
- [ ] Evidence attribution precision >85% (not yet measured against a real benchmark)
- [ ] Hallucination rate reduced by 40%+ vs. baseline (not yet measured)
- [ ] ArchEHR-QA: 75%+ claims fully supported (evaluation not started)
- [ ] Fitness recommendations working on demo data (not started)
- [x] Zero cloud data egress within `ml/` (local-only enforcement is code-level, not just audited)

### Research Success
- [ ] Two publication-ready research questions answered
- [ ] ArchEHR-QA benchmark results documented
- [ ] Ablation studies show evidence attribution adds value
- [x] Reproducible code — `ml/` is on GitHub with a live-tested pipeline and dated findings log (`docs/RESEARCH_LOG.md`)

### Product Success
- [ ] End-user demo works flawlessly (individual using PHIRE for their own health data, end-to-end through a UI — not built yet)
- [ ] README enables setup in <30 minutes (`ml/README.md` covers `ml/`; full-stack setup not yet documented end-to-end)
- [x] `ml/` code is clean, documented, tested (200+ tests, static-analysis clean)
- [ ] Deployment process automated (docker-compose)

---

## 🛑 Explicitly Out of Current Scope

- ❌ Advanced multimodal (images require more training data)
- ❌ Federated learning (infrastructure overhead)
- ❌ Voice interface (nice-to-have, not essential)
- ❌ Multilingual support (English only for now)
- ❌ FHIR representation (extend after core works)
- ❌ Wearable integration (Phase 3)
- ❌ Multi-hop graph-RAG retrieval (Phase 4 — see `docs/GRAPH_SCHEMA_ROADMAP.md` §3f; this is committed future scope, not indefinitely deferred)

**Rationale**: Ship core innovation (evidence attribution) first, iterate on extensions.

---

## 🔬 Competitive Positioning

Aiming to be among the first open-source systems with:
- ✅ Local inference (Ollama + medgemma:4b)
- ✅ Evidence attribution (NLI-based claim verification, not MedRAGChecker)
- ✅ Longitudinal reasoning (graph-backed trend computation)
- ❌ Fitness personalization (HAR + ML) — not started
- ✅ Hallucination detection

**Current competition**:
- Google Med-PaLM 2: Excellent but cloud-only (privacy risk)
- OpenAI GPT-4 Medical: Good but proprietary + expensive
- Claude 3.5: Strong but not healthcare-specialized
- No system studied combines local + evidence-attributed + longitudinal + personalized in one open-source stack

**PHIRE's angle**: local, evidence-attributed, open, healthcare-specific, published.

---

## 🎓 Research Contribution

**Paper 1**:
- Title: "Evidence-Attributed Medical Reasoning with Local LLMs"
- Contributions: Claim extraction + NLI-based verification + evaluation on ArchEHR-QA
- Novelty: Open-source healthcare evidence attribution system, benchmarked model choices at every stage (see `ml/*/experiments/RESULTS.md`)

**Paper 2**:
- Title: "Longitudinal Health Reasoning & Privacy-Utility Trade-offs in Local Models"
- Contributions: Temporal/trend reasoning + hallucination reduction + privacy analysis
- Novelty: Empirical study of local model scale vs. cloud models on this task

**Artifacts**:
- Open-source code + models
- ArchEHR-QA extended benchmark
- Reproducibility package (code + data + configs); `docs/RESEARCH_LOG.md` already tracks dated findings/decisions for this

---

**Status**: Core `ml/` scope implemented and live-tested; backend/frontend integration and extended phases outstanding.
**Risk Level**: Low for what's built (every component benchmarked, live-tested); unestimated for what isn't.
