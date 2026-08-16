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
│   ├── FEATURES_ALIGNED.md         # Feature spec (MVP + extended)
│   ├── AGGRESSIVE_ROADMAP.md       # 3-week MVP + 9-month timeline
│   ├── OPEN_SOURCE_TOOLS.md        # 40+ integrated tools & frameworks
│   └── DATASETS_AND_GRAPH_RAG.md   # Finalized datasets/models + graph RAG architecture
│
├── backend/                         # VARUN OWNS
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
├── frontend/                        # VARUN OWNS
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
├── ml/                              # ANIKA OWNS
│   ├── __init__.py
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── retriever.py            # Chroma + BM25 retrieval
│   │   ├── reranker.py             # Evidence ranking
│   │   └── embeddings.py           # Embedding pipeline
│   │
│   ├── claims/
│   │   ├── __init__.py
│   │   ├── extractor.py            # LLM claim extraction
│   │   ├── verifier.py             # MedRAGChecker integration
│   │   └── confidence.py           # Confidence scoring
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── prompt_builder.py       # Context + prompt construction
│   │   ├── ollama_client.py        # Ollama API wrapper
│   │   └── prompts.py              # Prompt templates
│   │
│   ├── recommendations/
│   │   ├── __init__.py
│   │   ├── fitness/
│   │   │   ├── har_model.py        # Activity recognition (PAMAP2)
│   │   │   └── recommendations.py  # Fitness suggestions
│   │   └── nutrition/
│   │       ├── model.py            # Nutrition model (month 6+)
│   │       └── meal_generator.py   # Meal plan generation
│   │
│   ├── chains/
│   │   ├── __init__.py
│   │   └── qa_chain.py             # LangChain QA pipeline
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
│   ├── Dockerfile.frontend
│   ├── docker-compose.yml          # All services
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
├── .gitignore
└── docker-compose.yml              # Master orchestration file
```

---

## 📁 Key Directories by Role

### Varun (ML & Intelligence)
- `ml/` - All ML components (RAG, claims, recommendations)
- `ml/rag/` - Retrieval and evidence ranking
- `ml/claims/` - Claim extraction and verification
- `ml/recommendations/` - Fitness and nutrition models

### Anika (Backend Infrastructure)
- `backend/` - FastAPI application, all server logic
- `docker/` - All containerization
- `scripts/` - Setup and run scripts

### Shashwati (Frontend & Evaluation)
- `frontend/` - Next.js application, UI components
- `evaluation/` - All metrics and benchmarking
- `evaluation/results/` - Metrics output, figures for paper
- `evaluation/notebooks/` - Analysis and statistical testing

---

## 🚀 Initialization

```bash
# Clone and setup
git clone https://github.com/varunaditya/PHIRE.git
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

**Status**: Structure ready for Week 1 development
