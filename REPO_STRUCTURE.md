# PHIRE: Repository Structure

**Layout**: Flat structure (no `src/` wrapper), subsystem folders at root.

```
phire/
├── README.md
├── CONTRIBUTING.md
├── GET_STARTED.md
├── CHANGELOG.md
│
├── docs/
│   ├── CODEBASE_AUDIT.md           # Master audit: features, inconsistencies, bugs, design choices
│   ├── BACKLOG.md                  # Known gaps, tech debt, open design questions
│   ├── API_REFERENCE.md            # Full request/response reference for every backend endpoint
│   ├── FRONTEND_HANDOFF.md         # Frontend UI architecture, page inventory, and active tasks
│   ├── BACKEND_HANDOFF.md          # backend/ <-> ml/ integration log: what changed, fixed, tested
│   ├── FEATURES_ALIGNED.md         # Feature checklist (core + extended, aligned to NLP-06)
│   ├── AGGRESSIVE_ROADMAP.md       # Build checklist: core MVP + extended features
│   ├── OPEN_SOURCE_TOOLS.md        # Tools catalog: adopted + evaluated candidates
│   ├── DATASETS_AND_GRAPH_RAG.md   # Finalized datasets/models + graph RAG architecture
│   ├── GRAPH_SCHEMA_ROADMAP.md     # Longitudinal Health Graph: current schema + deferred work
│   ├── PDF_INGESTION_ROADMAP.md    # Scanned-PDF ingestion gap: decided design, not yet built
│   ├── ML_HANDOFF_FOR_ANIKA.md     # ml/ -> backend/ integration contract
│   └── RESEARCH_LOG.md             # Dated findings/decisions for paper drafting
│
├── backend/                         # ANIKA OWNS — see backend/README.md
│   ├── README.md                    # API surface, architecture, configuration, quick start
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── .env.example
│   │
│   └── app/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app entry & middleware assembly
│       ├── config.py               # Pydantic Settings & environment variables
│       ├── security.py             # Localhost boundary & HIPAA audit middleware
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── router_health.py      # POST /api/health, GET /api/ping
│       │   ├── router_chat.py        # POST /api/chat, POST /api/chat/stream (SSE)
│       │   ├── router_documents.py   # POST /api/documents/upload, /process, GET /{id}, DELETE /{id}, GET /{id}/events (SSE)
│       │   ├── router_observations.py# GET /api/observations, GET /api/timeline
│       │   ├── router_search.py      # GET /api/search/evidence
│       │   ├── router_evidence.py    # POST /api/evidence/retrieve, POST /api/evidence/verify
│       │   ├── router_claims.py      # POST /api/claims/extract
│       │   └── router_recommendations.py # GET /api/recommendations/* (501 stubs)
│       │
│       ├── models/                 # Pydantic request/response schemas
│       │   ├── __init__.py
│       │   ├── document.py
│       │   ├── observation.py
│       │   ├── claim.py
│       │   └── response.py
│       │
│       ├── database/
│       │   ├── __init__.py
│       │   ├── connection.py       # PostgreSQL engine & sessionmaker
│       │   ├── schemas.py          # SQLAlchemy models (documents, chat_messages, claims, audit_log)
│       │   └── migrations/         # Alembic migration versions
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── document_processor.py  # Background ingestion & transactional rollback
│       │   ├── graph_reader.py        # Cypher queries for timeline & observations
│       │   ├── ml_singletons.py       # Lazy cached ML models & the process-wide GPU_LOCK
│       │   ├── gpu_modes.py           # gpu_mode(LIFT|CHAT): mutually exclusive GPU residency groups
│       │   ├── progress.py            # In-memory per-document event channel behind SSE
│       │   ├── evidence_search.py     # Shared retrieve→rerank→scored citations (search + /evidence/retrieve)
│       │   ├── citations.py           # Citation formatters
│       │   └── audit_logger.py        # Dual PostgreSQL & disk file audit logger
│       │
│       └── utils/
│           ├── __init__.py
│           ├── validators.py       # Upload size & MIME validation
│           ├── encryption.py       # Fernet symmetric encryption helper
│           └── constants.py        # Enums & MIME types
│
├── frontend/                        # SHASHWATI OWNS — see docs/FRONTEND_HANDOFF.md
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── postcss.config.mjs
│   ├── eslint.config.mjs
│   ├── README.md
│   │
│   ├── app/
│   │   ├── layout.tsx              # Root layout (fonts, ThemeProvider, Sidebar)
│   │   ├── globals.css             # Global Tailwind tokens & design tokens
│   │   ├── page.tsx                # Dashboard (timeline charts & observations)
│   │   ├── chat/
│   │   │   └── page.tsx            # Evidence-Attributed Medical Chat UI
│   │   ├── documents/
│   │   │   └── page.tsx            # Drag-and-drop document uploader & status
│   │   └── search/
│   │       └── page.tsx            # Hybrid evidence search & claim verifier
│   │
│   ├── components/
│   │   ├── sidebar.tsx             # Main navigation & theme toggle
│   │   ├── progress-steps.tsx      # Live SSE stage checklist (chat + documents)
│   │   └── theme-provider.tsx      # next-themes provider wrapper
│   │
│   ├── lib/
│   │   ├── api.ts                  # Typed backend fetch wrapper & models (+ chat.stream, documents.watch)
│   │   ├── sse.ts                  # fetch-based Server-Sent Events reader (works for POST)
│   │   └── utils.ts                # Tailwind clsx/twMerge utility
│   │
│   └── public/                     # Static assets & SVG icons
│
├── ml/                              # VARUN OWNS — see ml/README.md
│   ├── README.md                    # Architecture, quick start, model choices, feature status
│   ├── requirements.txt
│   ├── __init__.py
│   ├── local_only.py                # Universal localhost address validator
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── embeddings.py           # MedCPT query/article dual-encoder
│   │   ├── retriever.py            # Hybrid BM25 + Chroma retrieval with RRF fusion
│   │   ├── reranker.py             # MedCPT Cross-Encoder with structural patient floor
│   │   ├── ingest/                 # Document & reference ingestion pipeline
│   │   │   ├── ingest_patient_document.py  # Patient PDF/image ingestion coordinator
│   │   │   ├── run_ingest.py               # Reference ingestion runner (manifest generator)
│   │   │   ├── lift_extractor.py           # datalab-to/lift 9.7B VLM extractor (4-bit NF4 + CPU)
│   │   │   ├── lift_schema.py              # Clinical document schema & payload validator
│   │   │   ├── chunk_synthesizer.py        # Option A declarative clinical sentence synthesizer
│   │   │   ├── patient_documents.py        # Document format router via Lift
│   │   │   ├── chunking.py                 # Passage chunker with table parser helpers
│   │   │   ├── pubmed.py, medlineplus.py, usda.py, topics.py
│   │   │   ├── experiments/        # Vision OCR model selection benchmarks
│   │   │   └── router_experiments/ # OCR router benchmark
│   │   ├── reranker_experiments/   # Reranker tuning experiments & results
│   │   └── experiments/            # Embedding benchmark & candidate evaluations
│   │
│   ├── claims/
│   │   ├── __init__.py
│   │   ├── extractor.py            # Atomic claim extraction via medgemma:4b / qwen3.5:9b
│   │   ├── verifier.py             # BART-large-MNLI claim verifier
│   │   ├── confidence.py           # NLI confidence calculation
│   │   └── experiments/            # NLI model benchmark & candidate evaluations
│   │
│   ├── graph/                       # Longitudinal Health Graph (Neo4j)
│   │   ├── __init__.py
│   │   ├── client.py                # Localhost-enforced Neo4j client
│   │   ├── observations.py, medications.py, conditions.py  # Graph entity builders
│   │   ├── document_dates.py        # Day-first clinical date parser & ISO normalizer
│   │   ├── metric_resolver.py       # Canonical metric normalization dictionary
│   │   ├── patient_context.py       # Graph read queries & trend delta precomputation
│   │   ├── deletion.py              # Ingestion rollback node/edge cleanup
│   │   └── experiments/            # Extraction model benchmark & results
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── ollama_client.py        # Local Ollama HTTP client
│   │   ├── prompt_builder.py       # Context assembly & length truncation
│   │   └── prompts.py              # Medical system prompts & safety disclaimers
│   │
│   ├── recommendations/             # Post-MVP research stubs
│   │   ├── __init__.py
│   │   ├── fitness/ (har_model.py, recommendations.py)
│   │   └── nutrition/ (meal_generator.py, model.py)
│   │
│   ├── chains/
│   │   ├── __init__.py
│   │   └── qa_chain.py             # End-to-end Reverse-RAG orchestrator
│   │
│   └── tests/                       # ~227 pytest tests (220 pass without live GPU infra; live/integration ones need Ollama/Neo4j/free VRAM). conftest.py defaults lift to mock mode; test_gpu_modes.py / test_progress.py cover backend services
│
├── evaluation/                      # SHASHWATI OWNS (Planned / Scheduled)
│   └── (ArchEHR-QA & MedHallBench benchmarks)
│
├── docker/
│   ├── Dockerfile.backend          # Root context backend container (backend + ml dependencies)
│   ├── Dockerfile.backend.dockerignore
│   ├── Dockerfile.backend.standalone # Legacy standalone scaffold
│   ├── Dockerfile.frontend         # Next.js multi-stage build container
│   ├── docker-compose.yml          # Full-stack composition (Postgres, Ollama, Neo4j, Backend, Frontend)
│   └── nginx.conf                  # Host-networked reverse proxy
│
├── scripts/
│   ├── setup.sh                    # Shared environment & venv setup
│   ├── run.sh                      # Full-stack docker compose startup
│   ├── run_backend.sh              # Local FastAPI runner with Alembic migrations & PYTHONPATH
│   └── run_frontend.sh             # Local Next.js runner
│
├── data/
│   ├── chroma/                     # Chroma persistent vector store
│   ├── demo/                       # Demo patient records
│   ├── benchmarks/                 # Benchmark datasets
│   └── ingest_manifest.json        # Reference corpus metadata
│
├── archive/                         # Legacy research syntheses (read-only)
├── .env.example
└── .gitignore
```

---

## 📁 Key Directories by Role

### Varun (ML & Intelligence)
- `ml/README.md` - Start here: architecture, quick start, model choices, feature status
- `ml/rag/` - Retrieval, reranking, and document/reference ingestion
- `ml/claims/` - Claim extraction and NLI-based verification
- `ml/graph/` - Longitudinal Health Graph (Neo4j)
- `ml/recommendations/` - Fitness and nutrition models (research stubs)

### Anika (Backend Infrastructure)
- `backend/README.md` - Start here: API surface, architecture, configuration, quick start
- `backend/` - FastAPI application, routers, database schemas, services
- `docker/` - Containerization and orchestration
- `scripts/` - Setup and execution scripts

### Shashwati (Frontend & Evaluation)
- `docs/FRONTEND_HANDOFF.md` - Frontend UI architecture, page inventory, and active tasks
- `docs/API_REFERENCE.md` - Full request/response reference for every endpoint
- `frontend/` - Next.js application, UI components, API client
- `evaluation/` - Metrics, benchmarks, analysis (scheduled for evaluation phase)

---

## 🔗 Folder Ownership

| Folder | Owner | Responsibility |
|--------|-------|---|
| `backend/` | Anika | All FastAPI routes, models, database, services |
| `frontend/` | Shashwati | Next.js pages, components, styling, UI client |
| `ml/` | Varun | RAG, claims, graph, embeddings, chains, tests |
| `evaluation/` | Shashwati | Metrics, benchmarks, analysis (upcoming) |
| `docker/` | Anika | Containerization, orchestration, Nginx |
| `scripts/` | Anika | Setup and execution scripts |
| `data/` | All | Demo data, shared benchmarks, vector store |
| `docs/` | All | Documentation (everyone contributes) |
