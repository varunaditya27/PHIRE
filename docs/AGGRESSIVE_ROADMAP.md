# PHIRE: Aggressive Implementation Roadmap
## 3-Week MVP + 9-Month Extended (2023-2026 Tech Stack)

**Team**: Varun (ML & Intelligence), Anika (Backend Infrastructure), Shashwati (Frontend & Evaluation)
**Acceleration**: AI coding agents (1.5x realistic speedup, not hype)
**Research Basis**: 2023-2026 healthcare AI evolution analysis

---

## 🚀 3-WEEK MVP: AGGRESSIVE SCOPE

### Week 1: Foundation + First Features

**Days 1-2: Infrastructure Bootstrap**
- Ollama + MedGemma 1.5 (8B, 4.1GB quantized) → localhost:11434
- PostgreSQL (Docker) + pgvector extension
- Chroma vector DB (native Python, not Docker)
- FastAPI scaffold with async routing
- Next.js 15 setup with server components (keeps PHI server-side)
- **AI Agent**: Scaffold all boilerplate (3-5x speedup)
- **Deliverable**: All services running, basic API endpoints

**Days 3-4: Document Pipeline + RAG Core**
- PDF extraction (Docling) → normalized observations
- Chroma ingestion pipeline (embed clinical reference docs)
- BM25 lexical retrieval (exact term matching for lab values)
- LangChain RAG chain with Ollama
- Basic retrieval endpoint: `/api/evidence/retrieve`
- **AI Agent**: RAG integration boilerplate
- **Deliverable**: Query "LDL" → returns relevant evidence

**Days 5-7: Claim Extraction + Early Verification**
- LLM prompt for structured claim extraction (atomic facts)
- MedRAGChecker integration (evidence verification)
- Confidence scoring (SUPPORTED, DERIVED, INFERRED, UNCERTAIN)
- Entailment checking (does evidence support claim?)
- Early UI: Chat interface + clickable evidence highlights
- **AI Agent**: Prompt optimization, UI components
- **Deliverable**: `/api/chat` returns claims with evidence links

### Week 2: Medical Intelligence + Health Context

**Days 8-10: Longitudinal Reasoning**
- Health timeline construction (observations grouped by date)
- Temporal normalization (unit conversion, date alignment)
- Trend detection (simple: compare recent vs. 1-year-ago)
- LLM reasoning over timeline context
- Enhanced prompt: patient context + evidence + temporal patterns
- **AI Agent**: Timeline algorithms, context building
- **Deliverable**: System understands "your LDL has increased 18 points"

**Days 11-13: Fitness Recommendations + Hallucination Detection**
- Pre-trained HAR model (PAMAP2-based, activity recognition)
- Fitness recommendation engine (activity patterns → suggestions)
- Unsupported claim detection (flag claims without evidence)
- Abstention logic (refuse to answer if uncertain)
- Safety gates for high-risk claims (medications, diagnoses)
- **AI Agent**: Model integration, safety gate implementation
- **Deliverable**: System gives fitness advice + halts on unsupported health claims

**Days 14-15: Integration + Polish**
- Connect all subsystems (frontend ↔ backend ↔ RAG ↔ LLM ↔ HAR)
- Error handling, logging, HIPAA audit trails
- Caching layer (reduce LLM inference latency)
- Basic privacy audit (verify no cloud data egress)
- **AI Agent**: Integration scaffolding, tests
- **Deliverable**: Complete end-to-end system working

### Week 3: Evaluation + Documentation

**Days 16-18: Rigorous Testing**
- ArchEHR-QA 2026 evaluation (167 expert cases)
- Compute baseline metrics:
  - Evidence attribution accuracy (precision/recall)
  - Claim extraction quality
  - Hallucination rate
  - Response latency (<3 sec target)
- Comparison: MedRAGChecker vs. baseline RAG
- **AI Agent**: Test case generation, metrics computation
- **Deliverable**: Quantified MVP performance

**Days 19-21: Demo + Production Readiness**
- Create 3 realistic clinician personas + demo scenarios
- End-to-end workflow testing (no errors)
- Production-grade error handling
- README + deployment guide
- GitHub Actions CI/CD setup (test on push)
- **AI Agent**: Docs generation, test automation
- **Deliverable**: Demo-ready system, GitHub-ready code

---

## 📊 MVP Feature Matrix

| Feature | Effort | Status | Research Value |
|---------|--------|--------|-----------------|
| Local LLM inference | 20 hrs | ✅ | Baseline |
| Evidence attribution | 60 hrs | ✅ | ⭐⭐⭐⭐⭐ |
| Longitudinal reasoning | 50 hrs | ✅ | ⭐⭐⭐⭐⭐ |
| Hallucination detection | 40 hrs | ✅ | ⭐⭐⭐⭐ |
| Document ingestion | 35 hrs | ✅ | ⭐⭐ |
| Fitness recommendations | 30 hrs | ✅ | ⭐⭐⭐⭐ |
| Health timeline | 25 hrs | ✅ | ⭐⭐⭐⭐ |
| ArchEHR-QA evaluation | 25 hrs | ✅ | ⭐⭐⭐⭐ |

**Total MVP**: 285 hours (without agents) → ~190 hours (with 1.5x acceleration)
**Per person**: ~63 hours (3 weeks × 15-16 hrs/week realistic)

---

## 🎯 Months 2-9: Extended Roadmap (Aggressive)

### Phase 2: Advanced Evidence & ML (Months 2-3)

**Month 2 Focus**: Enhance medical grounding + start ML
- Contradiction detection (conflicting lab values across visits)
- Evidence ranking (guidelines > RCTs > obs. data)
- Multi-modal document understanding (images + tables + text)
- Start nutrition recommendation data collection
- Privacy-utility benchmark (local 8B vs cloud models)
- **Effort**: 200 hours
- **Deliverable**: Production-grade medical reasoning

**Month 3 Focus**: Fitness ML + wearable integration
- Custom HAR fine-tuning on PHIRE user data (if available)
- Wearable API integration (Fitbit, Oura, Apple Health)
- Correlation analysis (activity patterns + health outcomes)
- Fitness recommendation personalization
- **Effort**: 180 hours
- **Deliverable**: Multi-modal health recommendations

### Phase 3: ML Models & Personalization (Months 4-6)

**Month 4**: Nutrition recommendation model training
- Collect 1-3 months real PHIRE nutrition data
- Train custom nutrition recommendation model (collaborative filtering + content-based)
- Integrate with evidence attribution (explain "why this recommendation")
- **Effort**: 150 hours

**Month 5**: Advanced temporal reasoning
- Trajectory prediction (will my glucose worsen?)
- Anomaly detection (unusual health patterns)
- Multi-disease interaction modeling
- **Effort**: 120 hours

**Month 6**: Multimodal integration
- Medical image understanding (X-rays, lab graphs)
- Structured + unstructured data fusion
- Explainability improvements (show reasoning)
- **Effort**: 140 hours

### Phase 4: Production Hardening & Research (Months 7-9)

**Month 7**: Enterprise deployment
- Multi-region setup (hospital networks)
- Role-based access control (clinician vs. patient)
- Advanced audit logging for compliance
- **Effort**: 120 hours

**Month 8**: Regulatory preparation
- FDA 510(k) submission documentation
- Clinical validation studies
- Safety & efficacy write-ups
- **Effort**: 100 hours

**Month 9**: Publication & reproducibility
- Paper 1: Evidence attribution + longitudinal reasoning
- Paper 2: Hallucination detection + privacy-utility
- Reproducible artifacts (code + benchmark + datasets)
- Open-source release
- **Effort**: 150 hours

---

## 📈 Total Effort Breakdown

| Phase | Varun (ML) | Anika (Backend) | Shashwati (Frontend + Eval) | Total |
|-------|------------|------------------|--------------------------|-------|
| **MVP (3 wk)** | 115 hrs | 125 hrs | 170 hrs | 410 hrs |
| **Phase 2** | 100 hrs | 80 hrs | 80 hrs | 260 hrs |
| **Phase 3** | 180 hrs | 100 hrs | 120 hrs | 400 hrs |
| **Phase 4** | 120 hrs | 100 hrs | 200 hrs | 420 hrs |
| **TOTAL** | 515 hrs | 405 hrs | 570 hrs | 1490 hrs |

**Per person per week (9 months)**: 18-22 hours ✅ (realistic research load)
**With AI agents (1.5x)**: ~12-15 hours per person per week (very achievable)

---

## 🧠 AI Agent Acceleration Strategy

### High-Speedup Tasks (3-5x with agents)
- Boilerplate code generation (FastAPI routes, Next.js components)
- Test case generation (unit + integration tests)
- Documentation (API docs, deployment guides)
- Docker/deployment automation

### Medium-Speedup Tasks (2-3x with agents)
- Model integration scaffolding (RAG, ML models)
- Database migrations & schema management
- API contract enforcement (Pydantic models)
- CI/CD pipeline setup

### Low-Speedup Tasks (1x, still human domain)
- Architecture decisions (which tech stack?)
- Research methodology (evaluation design)
- Safety/security architecture
- Regulatory compliance strategy
- Paper writing (core ideas)

### Net Effect: 1.5x Realistic Acceleration
- Don't believe marketing hype (2-3x claims)
- Plan conservatively (1.5x actual)
- Allocate agent-generated code review time
- Focus agents on high-repetition tasks

---

## 🎯 Success Metrics (End of MVP)

### Technical Success
- ✅ Response latency <3 seconds end-to-end
- ✅ Evidence attribution precision >85%
- ✅ Hallucination rate reduced by 40%+ vs. baseline
- ✅ ArchEHR-QA: 75%+ claims fully supported
- ✅ Fitness recommendations working on demo data
- ✅ Zero cloud data egress (privacy audit passes)

### Research Success
- ✅ Two publication-ready research questions answered
- ✅ ArchEHR-QA benchmark results documented
- ✅ Ablation studies show evidence attribution adds value
- ✅ Reproducible code ready for GitHub

### Product Success
- ✅ Clinician demo works flawlessly (3 personas)
- ✅ README enables setup in <30 minutes
- ✅ Code is clean, documented, production-ready
- ✅ Deployment process automated (docker-compose)

---

## 🛑 What's NOT in MVP (Explicitly Deferred)

- ❌ Advanced multimodal (images require more training data)
- ❌ Federated learning (infrastructure overhead)
- ❌ Voice interface (nice-to-have, not essential)
- ❌ Multilingual support (English only for MVP)
- ❌ FHIR representation (extend after core works)
- ❌ Wearable integration (simplified in MVP, full in Phase 3)

**Rationale**: Ship core innovation (evidence attribution) quickly, iterate on extensions.

---

## 🔬 Competitive Positioning

**6-12 month window** to be first open-source system with:
- ✅ Local inference (Ollama MedGemma)
- ✅ Evidence attribution (MedRAGChecker)
- ✅ Longitudinal reasoning (temporal LLM)
- ✅ Fitness personalization (HAR + ML)
- ✅ Hallucination detection

**Current competition**:
- Google Med-PaLM 2: Excellent but cloud-only (privacy risk)
- OpenAI GPT-4 Medical: Good but proprietary + expensive
- Claude 3.5: Strong but not healthcare-specialized
- **No one has all four together** (local + evidence + temporal + personalization)

**PHIRE advantage**: Be first, be open, be healthcare-specific, be published.

---

## 📅 Timeline Summary

```
Week 1-3:    MVP (infrastructure + core features)
Month 2:     Enhancement (evidence ranking, wearables)
Month 3:     Fitness ML (model training, personalization)
Month 4-6:   Nutrition ML (recommendation model)
Month 7:     Production hardening (enterprise deployment)
Month 8:     Regulatory (510(k) preparation)
Month 9:     Publication (paper + open-source)
```

**Key milestone**: Ship MVP by end of Week 3 for user testing and feedback loop

---

## 🎓 Research Contribution

**Publication Target**: ACL 2027 or EMNLP 2026

**Paper 1** (Months 4-5 writing):
- Title: "Evidence-Attributed Medical Reasoning with Local LLMs"
- Contributions: Claim extraction + verification + evaluation on ArchEHR-QA
- Novelty: First open-source healthcare evidence attribution system

**Paper 2** (Months 8-9 writing):
- Title: "Longitudinal Health Reasoning & Privacy-Utility Trade-offs in Local Models"
- Contributions: Temporal reasoning + hallucination reduction + privacy analysis
- Novelty: Empirical study of 8B local vs 70B cloud models

**Artifacts**:
- Open-source code + models
- ArchEHR-QA extended benchmark
- Reproducibility package (code + data + configs)

---

**Status**: Aggressive but realistic
**Risk Level**: Low (every component proven in 2023-2026 research)
**Team Capacity**: Exactly matched to 9-month timeline
**Competitive Window**: 6-12 months (move fast)

Ready to execute.
