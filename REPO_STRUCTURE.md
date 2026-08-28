# PHIRE: Repository Structure

**Layout**: Flat structure (no `src/` wrapper), technology folders at root

```
phire/
├── README.md
├── CONTRIBUTING.md
├── GET_STARTED.md
├── CHANGELOG.md
│
├── docs/
│   ├── FEATURES_ALIGNED.md         # Feature checklist (core + extended)
│   ├── AGGRESSIVE_ROADMAP.md       # Build checklist: core MVP + extended features
│   ├── OPEN_SOURCE_TOOLS.md        # Tools catalog: adopted + evaluated-but-not-adopted candidates
│   ├── DATASETS_AND_GRAPH_RAG.md   # Finalized datasets/models + graph RAG architecture
│   ├── GRAPH_SCHEMA_ROADMAP.md     # Longitudinal Health Graph: current schema + deferred work
│   ├── PDF_INGESTION_ROADMAP.md    # Scanned-PDF ingestion gap: decided design, not yet built
│   ├── ML_HANDOFF_FOR_ANIKA.md     # ml/ -> backend/ integration contract
│   └── RESEARCH_LOG.md             # Dated findings/decisions, reusable for paper drafting
│
├── backend/                         # ANIKA OWNS — see backend/README.md
│   ├── README.md                    # API surface, architecture, configuration, quick start
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── config.py               # Settings, env vars
│   │   ├── security.py             # HIPAA, encryption, logging
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router_documents.py   # POST /api/documents/*
│   │   │   ├── router_observations.py # GET /api/patient/*/observations
│   │   │   ├── router_chat.py        # POST /api/chat
│   │   │   ├── router_search.py      # GET /api/search/*
│   │   │   ├── router_health.py      # POST /api/health
│   │   │   ├── router_evidence.py    # POST /api/evidence/retrieve, /verify
│   │   │   ├── router_claims.py      # POST /api/claims/extract
│   │   │   └── router_recommendations.py # GET /api/recommendations/*
│   │   │
│   │   ├── models/                 # Pydantic schemas
│   │   │   ├── document.py
│   │   │   ├── observation.py
│   │   │   ├── claim.py
│   │   │   └── response.py
│   │   │
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py       # PostgreSQL connection
│   │   │   ├── schemas.py          # SQLAlchemy models
│   │   │   └── migrations/         # Alembic migrations
│   │   │
│   │   ├── services/
│   │   │   ├── document_processor.py  # PDF → text (Docling, OCR)
│   │   │   ├── timeline_builder.py    # Temporal normalization
│   │   │   ├── embedding_service.py   # Vector DB interaction
│   │   │   └── audit_logger.py        # HIPAA compliance logging
│   │   │
│   │   └── utils/
│   │       ├── validators.py
│   │       ├── encryption.py
│   │       └── constants.py
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                        # SHASHWATI OWNS
│   ├── app/
│   │   ├── layout.tsx              # Root layout (auth, theme)
│   │   ├── page.tsx                # Home page
│   │   ├── globals.css             # Global styles
│   │   │
│   │   ├── dashboard/
│   │   │   ├── layout.tsx          # Dashboard layout
│   │   │   ├── page.tsx            # Dashboard home
│   │   │   ├── chat/
│   │   │   │   └── page.tsx        # Chat interface
│   │   │   ├── timeline/
│   │   │   │   └── page.tsx        # Health timeline view
│   │   │   └── documents/
│   │   │       └── page.tsx        # Document management
│   │   │
│   │   └── api/                    # Next.js API routes (proxy if needed)
│   │       └── health.ts
│   │
│   ├── components/
│   │   ├── ChatInterface.tsx       # Main chat component
│   │   ├── ChatMessage.tsx         # Individual message display
│   │   ├── EvidenceDisplay.tsx     # Source highlighting
│   │   ├── ClaimCard.tsx           # Individual claim
│   │   ├── Timeline.tsx            # Health timeline chart
│   │   ├── DocumentUpload.tsx      # File upload
│   │   ├── StreamingResponse.tsx   # Real-time LLM output
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   └── Layout.tsx
│   │
│   ├── hooks/
│   │   ├── useChat.ts              # Chat state management
│   │   ├── usePatientData.ts       # Patient context
│   │   └── useApi.ts               # API integration
│   │
│   ├── types/
│   │   ├── chat.ts
│   │   ├── patient.ts
│   │   ├── evidence.ts
│   │   └── api.ts
│   │
│   ├── lib/
│   │   ├── api-client.ts           # Axios/fetch wrapper
│   │   ├── utils.ts
│   │   └── constants.ts
│   │
│   ├── public/
│   │   ├── favicon.ico
│   │   └── images/
│   │
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── next.config.js
│   ├── Dockerfile
│   └── .env.example
│
├── ml/                              # VARUN OWNS — see ml/README.md
│   ├── README.md                    # Architecture, quick start, model choices, feature status
│   ├── __init__.py
│   ├── local_only.py                # Shared "must resolve to localhost" enforcement (Ollama, Neo4j)
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── retriever.py            # Chroma + BM25 hybrid retrieval (reciprocal rank fusion)
│   │   ├── reranker.py             # MedCPT cross-encoder + authority/recency scoring
│   │   ├── embeddings.py           # MedCPT dual-encoder embedding pipeline
│   │   ├── ingest/                 # Patient document + reference-evidence ingestion
│   │   │   ├── ingest_patient_document.py  # Entry point: PDF/image -> chunks + graph facts
│   │   │   ├── run_ingest.py               # Entry point: PubMed/MedlinePlus/USDA -> reference corpus
│   │   │   ├── ocr.py, patient_documents.py, chunking.py, table_parsing.py
│   │   │   ├── pubmed.py, medlineplus.py, usda.py, topics.py
│   │   │   └── experiments/        # OCR/router model-selection benchmarks
│   │   ├── reranker_experiments/   # Reranker weight-tuning benchmark
│   │   └── experiments/            # Embedding model-selection benchmark
│   │
│   ├── claims/
│   │   ├── __init__.py
│   │   ├── extractor.py            # LLM-based atomic claim extraction
│   │   ├── verifier.py             # NLI-based verification (BART-large-MNLI)
│   │   ├── confidence.py           # Confidence scoring
│   │   └── experiments/            # NLI model-selection benchmark
│   │
│   ├── graph/                       # Longitudinal Health Graph (Neo4j)
│   │   ├── client.py                # Neo4j driver wrapper (localhost-enforced)
│   │   ├── observations.py, medications.py, conditions.py  # Build + write typed facts
│   │   ├── document_dates.py        # Document date extraction (day-first, DOB-aware)
│   │   ├── metric_resolver.py       # Canonical lab/vital metric names
│   │   ├── prose_extraction.py      # LLM extraction of facts from free text
│   │   ├── patient_context.py       # Read path: current facts + trend deltas, feeds chat
│   │   └── experiments/            # Prose-extraction method/model benchmark
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── prompt_builder.py       # Context + prompt construction
│   │   ├── ollama_client.py        # Ollama API wrapper (medgemma:4b default)
│   │   └── prompts.py              # Prompt templates
│   │
│   ├── recommendations/             # Not yet implemented (stubs only)
│   │   ├── __init__.py
│   │   ├── fitness/
│   │   │   ├── har_model.py        # Activity recognition (PAMAP2) — planned
│   │   │   └── recommendations.py  # Fitness suggestions — planned
│   │   └── nutrition/
│   │       ├── model.py            # Nutrition model — planned
│   │       └── meal_generator.py   # Meal plan generation — planned
│   │
│   ├── chains/
│   │   ├── __init__.py
│   │   └── qa_chain.py             # Hand-written QA orchestration (retrieve -> generate -> verify -> abstain)
│   │
│   ├── tests/                       # pytest suite: unit, live-Neo4j integration, live end-to-end
│   │
│   └── requirements.txt
│
├── evaluation/                      # SHASHWATI OWNS
│   ├── __init__.py
│   ├── metrics.py                  # Evidence attribution, hallucination metrics
│   ├── baselines.py                # RAG baseline comparison
│   ├── benchmarks/
│   │   ├── archehr_qa.py           # ArchEHR-QA evaluation
│   │   └── medhallbench.py         # Hallucination benchmark
│   ├── ablations.py                # Ablation studies
│   ├── utils.py
│   ├── results/
│   │   ├── metrics_summary.json
│   │   ├── ablation_results.csv
│   │   └── figures/
│   │       ├── accuracy_comparison.png
│   │       ├── ablation_impact.png
│   │       └── latency_profile.png
│   └── notebooks/
│       ├── analysis.ipynb          # EDA, results exploration
│       └── statistical_tests.ipynb
│
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.backend.dockerignore
│   ├── Dockerfile.backend.standalone  # ml/-free single-service build
│   ├── Dockerfile.frontend
│   ├── docker-compose.yml          # All services — sole compose file
│   └── nginx.conf                  # Reverse proxy (optional)
│
├── scripts/
│   ├── setup.sh                    # Install dependencies
│   ├── run.sh                      # Start all services
│   ├── run_backend.sh
│   ├── run_frontend.sh
│   ├── eval.sh                     # Run evaluation
│   └── demo.sh                     # Demo walkthrough
│
├── data/
│   ├── demo/
│   │   ├── patient_1.json          # Sample patients
│   │   ├── patient_2.json
│   │   └── patient_3.json
│   └── benchmarks/
│       ├── archehr_qa.json         # Evaluation dataset reference
│       └── medhallbench.json
│
├── archive/
│   └── COMPREHENSIVE_SYNTHESIS.md  # Extended reference (read-only)
│
├── .env.example
└── .gitignore
```

---

## 📁 Key Directories by Role

### Varun (ML & Intelligence)
- `ml/README.md` - Start here: architecture, quick start, model choices, feature status
- `ml/` - All ML components (RAG, claims, graph, recommendations)
- `ml/rag/` - Retrieval, reranking, and document/reference ingestion
- `ml/claims/` - Claim extraction and NLI-based verification
- `ml/graph/` - Longitudinal Health Graph (Neo4j)
- `ml/recommendations/` - Fitness and nutrition models (not yet implemented)

### Anika (Backend Infrastructure)
- `backend/README.md` - Start here: API surface, architecture, configuration, quick start
- `backend/` - FastAPI application, all server logic
- `docker/` - All containerization
- `scripts/` - Setup and run scripts

### Shashwati (Frontend & Evaluation)
- `docs/FRONTEND_HANDOFF.md` - Start here: what's built in backend/ml, how to run the stack, gotchas
- `docs/API_REFERENCE.md` - Full request/response reference for every endpoint
- `frontend/` - Next.js application, UI components
- `evaluation/` - All metrics and benchmarking
- `evaluation/results/` - Metrics output, figures for paper
- `evaluation/notebooks/` - Analysis and statistical testing

---

## 🚀 Initialization

```bash
# Clone and setup
git clone https://github.com/varunaditya27/PHIRE.git
cd PHIRE

# Copy environment templates
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Install & run all services
bash scripts/setup.sh
bash scripts/run.sh
```

All services start:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Ollama: http://localhost:11434
- PostgreSQL: localhost:5432
- Chroma: http://localhost:8100 (if using container)

---

## 🔗 Folder Ownership

| Folder | Owner | Responsibility |
|--------|-------|---|
| `backend/` | Anika | All FastAPI routes, models, database |
| `frontend/` | Shashwati | All Next.js pages, components, styling |
| `ml/` | Varun | RAG, claims, embeddings, recommendations |
| `evaluation/` | Shashwati | Metrics, benchmarks, analysis |
| `docker/` | Anika | Containerization, orchestration |
| `scripts/` | Anika | Setup and execution scripts |
| `data/` | All | Demo data, shared benchmarks |
| `docs/` | All | Documentation (everyone contributes) |

---

## 🚨 Communication Points

**Varun ↔ Anika**:
- Anika's `/api/observations` endpoint → Varun's RAG context
- Varun's `/api/chat` response format (claims + evidence) → Anika's backend integration

**Varun ↔ Shashwati**:
- Varun's structured claims/evidence → Shashwati's evaluation metrics
- Shashwati's ablation results → Varun's prompt/model tuning

**Anika ↔ Shashwati**:
- Anika's FastAPI backend APIs → Shashwati's frontend integration
- Anika's raw data access → Shashwati's evaluation scripts

---

**Status**: `ml/` (RAG, claims, graph) implemented per the tree above; `backend/`, `frontend/`, `evaluation/` structure below is the planned layout, not yet built out — see each folder's own state before assuming this tree is current outside `ml/`.
