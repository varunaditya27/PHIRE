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
- **RAG System**: Evidence retrieval, ranking, reranking
- **MedRAGChecker**: Claim verification, entailment, confidence scoring
- **LangChain**: LLM chains, tool integration, RAG orchestration
- **ML Models**: Fitness HAR, nutrition recommendations, embeddings
- **Sentence Transformers**: Medical embeddings, semantic search
- **Model Training**: Fine-tuning, recommendation system development

**Specific Subsystems**:

1. **Claim Extraction & Verification (Core Innovation)**
   - LLM prompts for atomic claim decomposition
   - MedRAGChecker integration (evidence grounding)
   - Confidence scoring (SUPPORTED/DERIVED/INFERRED/UNCERTAIN)
   - Claim-to-evidence mapping for frontend

2. **RAG Pipeline**
   - LangChain chains (retrieval → LLM → verification)
   - Hybrid search (BM25 + semantic)
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

**Effort (MVP)**: 140 hours
- RAG system: 40 hrs
- Prompt engineering: 30 hrs
- MedRAGChecker: 25 hrs
- Claim extraction: 20 hrs
- Recommendations: 20 hrs
- Integration: 5 hrs

**Non-Blocking**: 
- Use mock Ollama responses (simulate LLM)
- Test on synthetic data (Synthea)
- Mock backend APIs initially

---

### ANIKA U BHAT: Backend Infrastructure & Deployment

**Primary Domain**: Everything that keeps data local and secure

**Tech Stack Ownership**:
- **Ollama + MedGemma 1.5**: Model serving, quantization, inference
- **FastAPI**: API design, async routing, validation (Pydantic)
- **PostgreSQL**: Schema, migrations, encryption, audit logging
- **Chroma Vector DB**: Embedding pipeline, retrieval indexes
- **Docker & Deployment**: Containerization, docker-compose, CI/CD
- **Document Processing**: PDF extraction (Docling), OCR, normalization
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

4. **Document Processing**
   - PDF parsing (Docling) with layout preservation
   - Table extraction & normalization
   - Source provenance tracking (page numbers)
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

**Effort (MVP)**: 125 hours
- Infrastructure setup: 30 hrs
- FastAPI backend: 40 hrs
- Document pipeline: 25 hrs
- Database & encryption: 20 hrs
- Integration & optimization: 10 hrs

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
- **Tailwind CSS**: Styling, responsive design, clinician UX
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
   - Evidence strength badges (SUPPORTED, INFERRED, etc.)
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

**Effort (MVP)**: 170 hours
- Frontend chat UI: 40 hrs
- Evidence display component: 25 hrs
- Timeline visualization: 20 hrs
- Document upload & management: 15 hrs
- Evaluation framework: 30 hrs
- ArchEHR-QA integration: 20 hrs
- Metrics & statistical analysis: 20 hrs

**Non-Blocking**: 
- Build frontend with mock API responses
- Create evaluation scripts without live system
- Test metrics on dummy data
- Design experiments while others code

---

## 📋 Week-by-Week Parallel Execution

### WEEK 1: Foundation (All Three Building Independently)

**Varun** (40 hrs) - ML & Intelligence:
- [ ] Download embedding model (medical-specialized)
- [ ] Setup Chroma vector DB (native Python)
- [ ] Ingest 50+ clinical reference documents
- [ ] Design LLM prompt for claim extraction (v1)
- [ ] Design MedRAGChecker integration
- [ ] Mock RAG chain (doesn't need Anika's API yet)

**Anika** (40 hrs) - Backend Infrastructure:
- [ ] Ollama + MedGemma 1.5 running locally
- [ ] PostgreSQL + pgvector Docker setup
- [ ] FastAPI project scaffold (routes, logging)
- [ ] Basic API endpoints (health check, upload stub)
- [ ] Docker-compose file for all services
- [ ] Database schema + migrations

**Shashwati** (50 hrs) - Frontend & Evaluation:
- [ ] Next.js 15 project setup (app router, TypeScript)
- [ ] Chat component scaffold (input + response display)
- [ ] Tailwind CSS + responsive layout
- [ ] Create 10 evaluation questions with expert answers
- [ ] Download ArchEHR-QA 2026 dataset
- [ ] Design evaluation metrics (precision, recall, F1)

### WEEK 2: Feature Implementation (Start Integration)

**Varun** (50 hrs) - ML & Intelligence:
- [ ] Implement RAG chain (retrieve → rerank → LLM → claims)
- [ ] Implement claim extraction from LLM output
- [ ] Integrate MedRAGChecker (evidence verification)
- [ ] Implement fitness recommendation engine
- [ ] Format responses for frontend (JSON claims + evidence)

**Anika** (35 hrs) - Backend Infrastructure:
- [ ] Implement `/api/documents/upload` endpoint
- [ ] Implement document processing pipeline
- [ ] Create `/api/patient/{id}/observations` endpoint
- [ ] Implement health timeline construction
- [ ] Add HIPAA audit logging

**Shashwati** (50 hrs) - Frontend & Evaluation:
- [ ] Connect Next.js frontend to Anika's FastAPI backend
- [ ] Implement ChatInterface component (consume `/api/chat`)
- [ ] Implement EvidenceDisplay component (show sources)
- [ ] Implement Timeline visualization component
- [ ] Setup evaluation metrics (Python functions)
- [ ] Create ArchEHR-QA benchmark runner

### WEEK 3: Polish & Evaluation (Final Integration)

**Varun** (25 hrs) - ML & Intelligence:
- [ ] Fine-tune prompts based on early results
- [ ] Improve evidence ranking (test strategies)
- [ ] Optimize recommendation quality
- [ ] End-to-end testing (full workflows)
- [ ] Handle edge cases (empty results, conflicting evidence)

**Anika** (30 hrs) - Backend Infrastructure:
- [ ] Performance optimization (caching, query tuning)
- [ ] Production-grade error handling
- [ ] Deploy docker-compose setup
- [ ] Privacy audit (no cloud egress verification)
- [ ] Health checks & monitoring

**Shashwati** (45 hrs) - Frontend & Evaluation:
- [ ] Polish frontend UI (styling, animations, clinician UX)
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

- ✅ Clinician can upload lab report
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
