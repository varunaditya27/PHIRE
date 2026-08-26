# PHIRE: Contributing & Team Work Division

**Team**: Varun Aditya, Anika U Bhat, M Shashwati Rao  
**Model**: Parallel subsystems, clear API boundaries (zero blocking)  
**Coordination**: Daily 5-min standup (9 AM), weekly sync (Friday 3 PM)

---

## 🎯 Role Division

### VARUN ADITYA: Machine Learning & Intelligence

**Primary Domain**: Making PHIRE smart—RAG, evidence attribution, recommendations

**Tech Stack Ownership**:
- **LLM Prompting**: Prompt engineering, chain-of-thought, reasoning
- **RAG System**: Evidence retrieval, ranking, reranking (MedCPT dual encoder + cross-encoder)
- **Claim Verification**: NLI-based entailment/contradiction scoring (BART-large-MNLI), confidence scoring
- **QA Orchestration**: Hand-written pipeline (`ml/chains/qa_chain.py`) — evaluated LangChain, went custom instead (see `docs/OPEN_SOURCE_TOOLS.md`)
- **Longitudinal Health Graph**: Neo4j, queried directly via Cypher (`ml/graph/`)
- **ML Models**: Fitness HAR, nutrition recommendations, embeddings
- **Sentence Transformers**: Medical embeddings, semantic search
- **Model Training**: Fine-tuning, recommendation system development

**Specific Subsystems**:

1. **Claim Extraction & Verification (Core Innovation)**
   - LLM prompts for atomic claim decomposition
   - NLI-based evidence grounding (`ml/claims/verifier.py`, BART-large-MNLI — chosen after benchmarking 6 candidates including medical-specialized models)
   - Status taxonomy: SUPPORTED / DERIVED / CONFLICTING / UNCERTAIN / UNSUPPORTED — DERIVED is a relabel applied one layer up (`ml/chains/qa_chain.py`) for claims that match a precomputed trend; INFERRED (multi-hop reasoning) is not implemented, no validated signal for it yet
   - Claim-to-evidence mapping for frontend

2. **RAG Pipeline**
   - Hand-written retrieval → generate → verify chain (`ml/chains/qa_chain.py`)
   - Hybrid search (BM25 + semantic, reciprocal rank fusion)
   - Evidence reranking (authority, recency, relevance)
   - Source passage extraction with locations

3. **Fitness Recommendations**
   - Pre-trained HAR model (PAMAP2-based)
   - Activity pattern recognition
   - Personalized suggestions with evidence

4. **Nutrition Recommendations** (Month 6+)
   - Recommendation model training
   - Recipe/meal suggestion generation
   - Macro/micronutrient alignment
   - Evidence-backed explanations

5. **Integration Layer**
   - LLM output → structured claims (JSON)
   - Evidence formatting for frontend
   - Streaming response handling
   - Multi-turn context management

**API Contracts** (what Varun provides):
```
POST /api/chat                    # query → structured answer + claims
POST /api/evidence/retrieve       # retrieve & rank evidence
POST /api/evidence/verify         # verify individual claims
POST /api/claims/extract          # extract atomic claims from text
GET  /api/recommendations/fitness # personalized fitness suggestions
GET  /api/recommendations/nutrition # nutrition recommendations
```

**Non-Blocking**: 
- Use mock Ollama responses (simulate LLM)
- Test on synthetic data (Synthea)
- Mock backend APIs initially

---

### ANIKA U BHAT: Backend Infrastructure & Deployment

**Primary Domain**: Everything that keeps data local and secure

**Tech Stack Ownership**:
- **Ollama + medgemma:4b**: Model serving, quantization, inference
- **FastAPI**: API design, async routing, validation (Pydantic)
- **PostgreSQL**: Schema, migrations, encryption, audit logging (relational only — Chroma is the vector store, not pgvector)
- **Chroma Vector DB**: Embedding pipeline, retrieval indexes (in-process, `ml/rag/retriever.py` owns the client)
- **Docker & Deployment**: Containerization, docker-compose, CI/CD
- **Document Processing**: already implemented in `ml/rag/ingest/` (pypdf for text PDFs, olmOCR-v2 for scans/photos) — Anika's scope here is backend wiring (`POST /api/documents/upload` calling into `ml/`), not building extraction from scratch
- **HIPAA Compliance**: Audit trails, data retention, security
- **DevOps**: Scripts, deployment automation, health checks

**Specific Subsystems**:

1. **LLM Service Layer**
   - Ollama deployment & health checks
   - Model quantization & memory optimization
   - Inference caching (prompt + KV cache)
   - Latency monitoring (<3 sec)

2. **Data Layer**
   - PostgreSQL schema (patients, observations, documents, claims, evidence)
   - Vector store indexing (Chroma)
   - Backup/recovery
   - Query optimization

3. **RAG Backend**
   - FastAPI endpoints for retrieval
   - Hybrid search (BM25 + semantic)
   - Reranking pipeline
   - Evidence embedding & storage

4. **Document Processing** (extraction implemented in `ml/rag/ingest/`; Anika's scope is backend wiring, not the extraction logic itself)
   - PDF/OCR text extraction (pypdf + olmOCR-v2, `ml/rag/ingest/patient_documents.py`) with layout-aware table parsing
   - Table extraction & normalization (`ml/rag/ingest/table_parsing.py`)
   - Source provenance tracking (exact character spans, `ml/rag/ingest/chunking.py`)
   - Metadata enrichment

5. **Security & Privacy**
   - TLS/SSL configuration
   - Database encryption
   - HIPAA audit logs
   - Data isolation (no cloud egress)
   - Privacy auditing

**API Endpoints** (what Anika provides):
```
POST /api/documents/upload           # File upload
POST /api/documents/process          # Extract observations
GET  /api/patient/{id}/observations  # Retrieve normalized data
GET  /api/patient/{id}/timeline      # Health timeline
POST /api/health                      # Service health check
GET  /api/search/evidence            # Full-text + semantic search
```

**Non-Blocking**: 
- Build APIs with mock LLM responses
- Build backend independently

---

### M SHASHWATI RAO: Frontend & Evaluation & Research

**Primary Domain**: User-facing experience + proof that PHIRE works

**Tech Stack Ownership**:
- **Next.js 15**: Frontend framework, server components, routing
- **React**: Components, hooks, state management
- **TypeScript**: Type safety, props validation
- **Tailwind CSS**: Styling, responsive design, individual-user UX (PHIRE is single-user/self-service, not clinician-facing)
- **Evaluation Framework**: Metrics, benchmarking, statistical testing
- **ArchEHR-QA 2026**: Integration, benchmark runner, failure analysis
- **Data Science**: Pandas, numpy, scikit-learn, scipy
- **Visualization**: Matplotlib, seaborn (charts for paper), recharts (UI)
- **Research**: Experimental design, ablations, significance testing
- **Paper Writing**: LaTeX, research communication

**Specific Subsystems**:

**FRONTEND**:
1. **Chat Interface**
   - Query input field with autocomplete
   - Response display with streaming (real-time)
   - Message history management
   - Loading/error states

2. **Evidence Display (Core UX)**
   - Clickable claims (highlight on hover)
   - Source passage highlighting
   - Evidence strength badges (SUPPORTED, DERIVED, CONFLICTING, UNCERTAIN, UNSUPPORTED)
   - Interactive evidence sidebar
   - Citation tooltips

3. **Health Timeline Visualization**
   - Interactive timeline chart (recharts)
   - Trend lines (LDL over months)
   - Clickable data points (show context)
   - Date range filtering
   - Health metrics summary

4. **Document Management**
   - File upload interface (drag-and-drop)
   - Upload progress indication
   - Document list with metadata
   - Delete/archive functions

5. **Accessibility & UX**
   - Keyboard navigation (tab through claims)
   - Screen reader support (WCAG AA)
   - Dark mode support
   - Mobile responsive (tablets)
   - Error boundaries + fallbacks

**EVALUATION**:
1. **Evaluation Metrics**
   - Evidence attribution precision/recall
   - Claim extraction quality
   - Hallucination detection rate
   - Response latency
   - F1 scores, AUC, confusion matrices

2. **Benchmark Integration**
   - ArchEHR-QA 2026 (167 expert cases) setup
   - Test/validation splits
   - Baseline RAG comparison
   - Ablation studies (what helps most?)

3. **Hallucination Detection**
   - Unsupported claim identification
   - Confidence calibration analysis
   - MedHallBench benchmark
   - Failure mode classification

4. **Research Analysis**
   - Privacy-utility curves (8B vs 70B models)
   - Statistical significance testing
   - Longitudinal reasoning accuracy
   - User study design (months 8+)

5. **Reproducibility & Artifacts**
   - Experimental config versioning
   - Results logging (all runs tracked)
   - Code reproducibility documentation
   - Open-source benchmark release

**Frontend Components**:
```
/frontend/app/
  ├── layout.tsx                     # Root layout, auth
  ├── page.tsx                       # Home page
  ├── dashboard/
  │   ├── page.tsx                  # Main dashboard
  │   ├── chat/page.tsx             # Chat interface
  │   ├── timeline/page.tsx         # Health timeline
  │   └── documents/page.tsx        # Document management
  └── components/
      ├── ChatInterface.tsx         # Chat component
      ├── EvidenceDisplay.tsx       # Evidence highlighting
      ├── Timeline.tsx              # Health timeline chart
      ├── ClaimCard.tsx             # Individual claim display
      └── StreamingResponse.tsx     # Real-time streaming
```

**Evaluation Deliverables**:
```
evaluation/
  ├── metrics.py                 # Metric implementations
  ├── baseline_comparison.py     # RAG vs evidence-attributed comparison
  ├── archehr_qa_eval.py        # ArchEHR-QA benchmark runner
  ├── results/
  │   ├── metrics_summary.json
  │   ├── ablation_studies.csv
  │   └── figures/               # Plots for paper
  └── notebooks/
      ├── analysis.ipynb         # EDA, results exploration
      └── statistical_tests.ipynb
```

**Non-Blocking**: 
- Build frontend with mock API responses
- Create evaluation scripts without live system
- Test metrics on dummy data
- Design experiments while others code

---

## 📋 Week-by-Week Parallel Execution

### WEEK 1: Foundation (All Three Building Independently)

**Varun** - ML & Intelligence: — all done
- [x] Download embedding model (medical-specialized) — MedCPT, benchmarked against 6 candidates
- [x] Setup Chroma vector DB (native Python)
- [x] Ingest 50+ clinical reference documents — PubMed/MedlinePlus/USDA corpus
- [x] Design LLM prompt for claim extraction (v1)
- [x] Design claim verification approach — NLI-based (BART-large-MNLI), not MedRAGChecker (not installable, see `docs/OPEN_SOURCE_TOOLS.md`)
- [x] Real RAG chain implemented (`ml/chains/qa_chain.py`) — superseded the original mock-chain plan

**Anika** - Backend Infrastructure:
- [ ] Ollama + medgemma:4b running locally
- [ ] PostgreSQL Docker setup (Chroma is the vector store, not pgvector — see `ml/rag/retriever.py`)
- [ ] FastAPI project scaffold (routes, logging)
- [ ] Basic API endpoints (health check, upload stub)
- [ ] Docker-compose file for all services
- [ ] Database schema + migrations

**Shashwati** - Frontend & Evaluation:
- [ ] Next.js 15 project setup (app router, TypeScript)
- [ ] Chat component scaffold (input + response display)
- [ ] Tailwind CSS + responsive layout
- [ ] Create 10 evaluation questions with expert answers
- [ ] Download ArchEHR-QA 2026 dataset
- [ ] Design evaluation metrics (precision, recall, F1)

### WEEK 2: Feature Implementation (Start Integration)

**Varun** - ML & Intelligence:
- [x] Implement RAG chain (retrieve → rerank → LLM → claims)
- [x] Implement claim extraction from LLM output
- [x] Implement NLI-based claim verification (`ml/claims/verifier.py`)
- [ ] Implement fitness recommendation engine — not started (`ml/recommendations/` is still stubs)
- [x] Format responses for frontend (JSON claims + evidence) — `ChatResponse`/`VerifiedClaim` dataclasses, JSON-serializable

**Anika** - Backend Infrastructure:
- [ ] Implement `/api/documents/upload` endpoint
- [ ] Implement document processing pipeline
- [ ] Create `/api/patient/{id}/observations` endpoint
- [ ] Implement health timeline construction
- [ ] Add HIPAA audit logging

**Shashwati** - Frontend & Evaluation:
- [ ] Connect Next.js frontend to Anika's FastAPI backend
- [ ] Implement ChatInterface component (consume `/api/chat`)
- [ ] Implement EvidenceDisplay component (show sources)
- [ ] Implement Timeline visualization component
- [ ] Setup evaluation metrics (Python functions)
- [ ] Create ArchEHR-QA benchmark runner

### WEEK 3: Polish & Evaluation (Final Integration)

**Varun** - ML & Intelligence:
- [ ] Fine-tune prompts based on real chat traffic (blocked on backend integration)
- [x] Improve evidence ranking — reranker weight-tuning benchmark + patient-document floor fix (`ml/rag/reranker_experiments/RESULTS.md`)
- [ ] Optimize recommendation quality — not started (`ml/recommendations/` is still stubs)
- [x] End-to-end testing (full workflows) — live pipeline tests against real Ollama/Neo4j/Chroma (`ml/tests/test_qa_chain_live_e2e.py`)
- [x] Handle edge cases (empty results, conflicting evidence, abstention)

**Anika** - Backend Infrastructure:
- [ ] Performance optimization (caching, query tuning)
- [ ] Production-grade error handling
- [ ] Deploy docker-compose setup
- [ ] Privacy audit (no cloud egress verification)
- [ ] Health checks & monitoring

**Shashwati** - Frontend & Evaluation:
- [ ] Polish frontend UI (styling, animations, individual-user UX)
- [ ] Frontend error handling (network errors, fallbacks)
- [ ] Accessibility (keyboard nav, WCAG AA compliance)
- [ ] Mobile responsiveness (tablets, different screens)
- [ ] Run full evaluation on demo scenarios (3 personas)
- [ ] Compute ablation studies (RAG vs baseline)
- [ ] Statistical significance testing
- [ ] Create visualizations for paper

---

## 🤝 Communication

### Daily Standup (9 AM, 5 min)
Each person: status + blockers + dependencies

### Weekly Sync (Friday 3 PM, 30 min)
- Progress updates (5 min each)
- Integration check: APIs working?
- Blockers: Any blocking dependencies?
- Next week: Priorities + handoffs
- Demo: Show working features

---

## ✅ MVP Deliverables (End of Week 3)

- ✅ User can upload their own lab report (PHIRE is single-user/self-service — not clinician-facing; the individual uploads their own records)
- ✅ Ask health questions
- ✅ See answers with evidence highlighted (clickable)
- ✅ View health timeline
- ✅ Get fitness recommendations
- ✅ System refuses unsupported claims
- ✅ All data stays local (privacy audit passes)
- ✅ Quantified baseline metrics

---

## 🚀 Contributing Guidelines

### Before Starting
1. Create GitHub Issue
2. Assign to yourself
3. Create feature branch
4. Discuss design if substantial changes

### During Development
1. Commit frequently (small, logical commits)
2. Write clear commit messages
3. Test locally before pushing
4. Push to feature branch daily
5. Mention blockers in standup

### Before Merging
1. Create Pull Request (link to Issue)
2. Self-review changes
3. Request review from appropriate owner:
   - ML/RAG/Claims changes → Varun review
   - Backend/Infrastructure/API → Anika review
   - Frontend/Evaluation/Research → Shashwati review
4. Address review comments
5. Merge when approved + tests pass

### Code Standards
- **Python**: PEP 8, type hints, Pydantic v2
- **TypeScript/React**: ESLint + Prettier, server components
- **Docstrings**: Brief (1-2 lines), focus on why
- **Testing**: Unit tests for logic, integration tests for APIs
- **Comments**: Only for non-obvious why, not what

---

**Status**: Ready for parallel development
