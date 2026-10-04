# PHIRE `backend/`: FastAPI, Ollama Serving, and Storage

**Owned by Anika (Backend Infrastructure).** The FastAPI service that
fronts PHIRE's storage (PostgreSQL) and orchestrates `ml/`'s RAG, claim
verification, and Longitudinal Health Graph pipeline for the frontend. See
the [root README](../README.md) for what PHIRE is as a whole; this doc
covers only `backend/`. See [docs/BACKEND_HANDOFF.md](../docs/BACKEND_HANDOFF.md)
for the detailed integration log (what changed, what was fixed, what was
tested) from wiring this layer to `ml/`'s real interfaces.

**Status**: Wired to `ml/`'s real interfaces end-to-end (retrieval →
generation → claim verification → confidence scoring, backed by real
Postgres/Neo4j/Chroma/Ollama, live-tested — see
[docs/BACKEND_HANDOFF.md §7](../docs/BACKEND_HANDOFF.md)), and running in Docker on
GPU or CPU. There is no dedicated `backend/tests/` directory yet; the backend's
services and HTTP endpoints are covered by tests living in `ml/tests/`
(`test_document_processor.py`, `test_document_date_endpoint.py`,
`test_gpu_modes.py`, `test_progress.py`, `test_evidence_search.py`,
`test_extractor_selection.py`) plus live integration runs. Router-level tests for
chat, search and the other routers are still to be written.

---

## 🎯 What `backend/` Does

- **API surface** for the frontend: chat, document upload/ingestion status,
  patient observations/timeline, evidence retrieval/verification, claim
  extraction, fitness/nutrition recommendations, health checks.
- **Orchestration, not business logic**: routers are thin passthroughs into
  `ml/`'s classes (`QAChain`, `HybridRetriever`, `ClaimVerifier`, etc, held
  as process-lifetime singletons in `app/services/ml_singletons.py`) — RAG,
  claim verification, and graph reasoning all live in `ml/`, not here.
- **Storage**: PostgreSQL via SQLAlchemy for relational data (documents —
  including each document's saved structured extraction, so a missing date
  can be fixed without re-running extraction — chat messages, claims, audit log). Chroma (vector) and Neo4j (graph) are owned
  and accessed exclusively through `ml/`'s own clients — backend never
  talks to them directly except via `ml/`.
- **Compliance**: request-level audit logging for every patient-data-facing
  endpoint (`app/security.py`'s `AuditMiddleware`) and an outbound-host
  allowlist enforcing PHIRE's no-cloud-calls invariant on any HTTP call
  backend itself makes (currently just the Ollama health probe).

---

## 🏗️ Architecture

```
Frontend (Next.js)
   │  HTTP
   ▼
FastAPI app (app/main.py)
   │  AuditMiddleware (patient-data endpoints only)
   ▼
Routers (app/api/*.py) ── thin passthroughs
   │
   ▼
ml_singletons.py (cached, lazy) ── QAChain / HybridRetriever / ClaimVerifier / OllamaClient / GraphClient
   │                                        │                    │
   ▼                                        ▼                    ▼
PostgreSQL (SQLAlchemy)              Chroma (via ml/)      Neo4j (via ml/)
```

## 📡 API Surface

| Prefix | Endpoints | Backed by |
|---|---|---|
| `/api/health` | `POST /api/health` | Postgres, Ollama, Chroma, Neo4j connectivity |
| `/api/documents` | `GET ` (list), `POST /upload`, `POST /{id}/process`, `GET /{id}`, `PUT /{id}/date`, `DELETE /{id}`, `GET /{id}/events` (SSE; `router_document_events.py`) | `ml.rag.ingest`, `ml.graph` (background task); events from `services/progress.py`; `PUT …/date` rebuilds facts and chunks from the saved extraction |
| `/api/observations`, `/api/timeline` | `GET /api/observations`, `GET /api/timeline` | `ml.graph` (via `graph_reader.py`) |
| `/api/search` | `GET /evidence` | `ml.rag.retriever.HybridRetriever` |
| `/api/chat` | `POST /api/chat`, `POST /api/chat/stream` (SSE), `GET /api/chat/messages` | `ml.chains.qa_chain.QAChain` |
| `/api/claims` | `POST /extract` | `ml.claims.extractor.ClaimExtractor` |
| `/api/evidence` | `POST /retrieve`, `POST /verify` | `ml.rag.retriever`, `ml.claims.verifier` |
| `/api/recommendations` | `GET /fitness`, `GET /nutrition` | `ml.recommendations.*` (nutrition is a stub — 501) |

The two SSE endpoints stream stage-by-stage progress (`progress` events, then a terminal `result`/`error` for chat; replay-then-live until `processed`/`failed` for documents) — frame formats in [docs/API_REFERENCE.md](../docs/API_REFERENCE.md). Every GPU-touching route runs inside `gpu_mode(...)` (`services/gpu_modes.py`): the lift group and the chat-model group are mutually exclusive on an 8GB GPU — see [docs/BACKEND_HANDOFF.md §9](../docs/BACKEND_HANDOFF.md).

`/api/ping` (in `app/main.py`) is a bare liveness check, separate from the
dependency-checking `/api/health`.

---

## ⚙️ Configuration

Settings load from `backend/.env` (see `backend/.env.example`) via
`app/config.py`'s pydantic-settings `Settings`. Key variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string |
| `OLLAMA_HOST`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS` | Passed explicitly into `ml/`'s `OllamaClient` (not read from `ml/`'s own env fallbacks — see `ml_singletons.py`'s docstring). The timeout is honored since `[0.9.0]`; raise it on CPU-only machines |
| `PHIRE_EXTRACTOR`, `OLLAMA_VISION_MODEL` | Document extractor: `auto` (lift on a CUDA GPU with lift-pdf installed, else the Ollama vision model), `lift`, or `ollama`; the vision model defaults to `OLLAMA_MODEL`. See [docs/CPU_SETUP.md](../docs/CPU_SETUP.md) |
| `LIFT_MODEL`, `LIFT_DEVICE`, `PHIRE_MOCK_LIFT` | Lift settings (GPU variant); `PHIRE_MOCK_LIFT=true` returns canned extractions for tests |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Passed into `ml/`'s `GraphClient` |
| `CHROMA_PERSIST_DIR` | Must match `ml/`'s own default so both processes share one physical store |
| `UPLOAD_DIR` | Where uploaded documents are stored before ingestion |
| `UPLOAD_MAX_SIZE_BYTES` | Enforced while streaming the upload, not after buffering it fully |
| `CORS_ORIGINS` | Frontend origin(s) allowed to call this API |

Any HTTP call backend makes must target a host in
`app/security.py`'s `ALLOWED_OUTBOUND_HOSTNAMES` (localhost/127.0.0.1/::1
only) — enforced via `is_outbound_host_allowed()`, checked before the
Ollama health probe. `ml/`'s own Ollama/Neo4j clients enforce the same
invariant independently via `ml.local_only.require_localhost()`.

---

## 🚀 Quick Start

**Local (no Docker), for backend development:**
```bash
scripts/setup.sh          # venv + backend/requirements.txt + ml/requirements.txt (+ ml/requirements-lift.txt on a GPU machine;
                          # CPU-only machines get CPU PyTorch and no lift — force with PHIRE_VARIANT=gpu|cpu)
cp backend/.env.example backend/.env   # fill in DATABASE_URL, OLLAMA_HOST/MODEL, NEO4J_URI/USER/PASSWORD, CHROMA_PERSIST_DIR
# have Postgres, Neo4j, and Ollama reachable at those addresses
scripts/run_backend.sh    # alembic upgrade head + uvicorn --reload, PYTHONPATH set to repo root
```

**Full stack (Docker):** see the [root README](../README.md)'s Quick Start,
or [docs/BACKEND_HANDOFF.md §8](../docs/BACKEND_HANDOFF.md) for the
Docker-specific run/verify sequence and platform caveats (host networking).
`scripts/run.sh` picks the GPU or CPU variant automatically; for a laptop without
an NVIDIA GPU see [docs/CPU_SETUP.md](../docs/CPU_SETUP.md).

**Verify it's working:**
```bash
curl -X POST http://localhost:8000/api/health
```

---

## 📁 Layout

```
backend/
├── app/
│   ├── main.py                # FastAPI app assembly — no request logic here
│   ├── config.py               # pydantic-settings Settings
│   ├── security.py             # AuditMiddleware, outbound-host allowlist
│   ├── api/                    # routers — thin passthroughs into ml/ (router_document_events.py holds the SSE route)
│   ├── database/                # SQLAlchemy models, connection, Alembic migrations
│   ├── models/                  # Pydantic request/response schemas
│   ├── services/                 # ml_singletons.py, gpu_modes.py (LIFT/CHAT GPU residency), progress.py (SSE event channel), evidence_search.py (retrieve→rerank→scored citations), document_processor.py (ingest + redate), audit_logger.py, citations.py, graph_reader.py
│   └── utils/                    # constants, validators, encryption, sse.py (SSE framing)
├── alembic.ini
└── requirements.txt
```

---

## Not Owned Here

RAG, claim extraction/verification, the Longitudinal Health Graph, and
fitness/nutrition recommendation models all live in `ml/` — see
[ml/README.md](../ml/README.md). Docker/orchestration lives in `docker/`
(see its files' own header comments); local scripts live in `scripts/`.
