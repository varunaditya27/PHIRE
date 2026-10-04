# Backend Handoff

Owner: Anika — Backend Infrastructure (FastAPI, Ollama, PostgreSQL, Chroma, Docker, Neo4j).

This documents the backend as it now stands: fully wired to the real `ml/` package (not a stub/fallback), tested end-to-end against real Postgres, Neo4j, and Ollama (real `medgemma:4b` + `qwen3.5:9b`), with accurate, verified results. It replaces the "Phase 2/3 fallback" scaffolding that shipped at Week 1 kickoff.

## 1. What changed and why

The backend was originally built against a *guessed* `ml/` interface (module-level `retrieve()`/`answer()`/`extract()`/`verify()` functions, threaded with a `patient_id` on every call). The actual `ml/` package that landed exposes **classes**, not module functions (`QAChain`, `HybridRetriever`, `ClaimExtractor`, `ClaimVerifier`, `GraphClient`), and is **hardcoded to a single patient** (`Patient {id: "self"}` in Neo4j) — there's no `patient_id` concept anywhere in `ml/`.

Three decisions were made explicitly (with the project owner) before rewiring:

1. **Single-patient, not multi-patient.** `patient_id` has been dropped from every route, Postgres table, and Pydantic model. PHIRE runs as one local instance per person, matching `ml/`'s actual design.
2. **Document ingestion now calls `ml/`'s real pipeline**, not backend's own (weaker, duplicate) PyMuPDF+regex extractor. Backend's `document_processor.py` is now a thin orchestrator that mirrors `ml/rag/ingest/ingest_patient_document.py`'s `main()` sequence.
3. **`/api/chat` is non-streaming JSON.** `QAChain.answer()` is a single blocking call with no token-level streaming (the final answer is built only from verified claims, so there are no tokens worth streaming). Stage-level progress *is* streamed since 2026-10-04 via the additive `POST /api/chat/stream` and `GET /api/documents/{id}/events` SSE endpoints — see §9.

## 2. Architecture

```
Frontend (Next.js)
    │ HTTP :3000 (dev default; :3001 if 3000 is taken) → :8000
    ▼
FastAPI Backend (backend/app/)
    │ in-process Python imports (NOT HTTP) via app/services/ml_singletons.py
    ▼
ml/  (Varun's scope — QAChain, HybridRetriever, LiftExtractor,
      ClaimVerifier, GraphClient — all real, all wired)
    │
    ├──→ Ollama (localhost:11434) — medgemma:4b (chat)
    ├──→ Lift VLM (in-process / vLLM) — datalab-to/lift (single-pass visual extraction)
    ├──→ Chroma (in-process, shared REPO_ROOT/data/chroma, collection
    │    "phire_evidence") — one physical store, one schema, owned by
    │    ml/rag/retriever.py
    └──→ Neo4j (bolt://localhost:7687 by default; :7688 if 7687 is taken) — Longitudinal Health Graph
         (Patient/Observation/Medication/Condition), owned by ml/graph/

PostgreSQL (backend-owned, relational bookkeeping only):
    documents (upload metadata), chat_messages, claims (schema exists,
    currently unwritten — see §6), audit_log
```

Postgres and Neo4j are **not duplicate stores of the same data**. Postgres never holds patient facts (labs/meds/conditions) — those live only in Neo4j, populated by `ml/graph`. Postgres holds upload bookkeeping and conversation history only.

## 3. How each route is wired

| Route | Backed by | Notes |
|---|---|---|
| `POST /api/chat` | `ml.chains.qa_chain.QAChain` (singleton) | Full retrieve→rerank→generate→extract→verify→abstain pipeline. Returns `{answer, claims, id, created_at}`. Every claim carries `status`, `confidence`, and a citation (`source_url` / `source_filename` + `source_span`, or neither if the evidence was a graph fact). |
| `GET /api/search/evidence`, `POST /api/evidence/retrieve` | `ml.rag.retriever.HybridRetriever` (singleton) | Real BM25 + semantic hybrid search via reciprocal rank fusion. |
| `POST /api/evidence/verify` | `HybridRetriever` + `ml.claims.verifier.ClaimVerifier` (singletons) | Re-retrieves using the claim text as the query (the request contract only carries the claim, not evidence), then runs real NLI verification. |
| `POST /api/claims/extract` | `ml.claims.extractor.ClaimExtractor` (singleton) | Returns unverified claim strings (status always `UNCERTAIN` — extraction alone doesn't verify). |
| `POST /api/documents/upload`, `/{id}/process`, `GET /{id}` | `app/services/document_processor.py` → `ml.rag.ingest` + `ml.graph` | Runs in a `BackgroundTask`. Extracts text, chunks + indexes into the shared retriever, extracts table + prose facts, writes them to Neo4j. Upload metadata/status lives in Postgres `documents`. |
| `GET /api/observations`, `GET /api/timeline` | `app/services/graph_reader.py` → `ml.graph.client.GraphClient` (raw Cypher) | Reads Observation/Medication/Condition nodes directly from Neo4j — **not** `ml.graph.patient_context` (that module returns pre-formatted prose sentences for the chat prompt, not structured fields; this reads the same schema via `GraphClient.run()`, `ml/`'s public Cypher API). |
| `POST /api/health` | Postgres, Ollama `/api/tags`, `HybridRetriever` construction, `GraphClient` connectivity | All four now checked; `graph` is a new field on `HealthStatus`. |
| `GET /api/recommendations/*` | `ml.recommendations.*` | Correctly 501 — those modules are docstring-only stubs in `ml/`, not a backend gap. |

All `ml/` instances are built **once**, lazily, and cached (`app/services/ml_singletons.py`) — constructing `QAChain`/`ClaimVerifier`/`HybridRetriever` per-request would reload MedCPT + BART-large-MNLI + a Neo4j driver on every call, which `ml/`'s own docs explicitly warn against.

## 4. What was retired

- `backend/app/services/embedding_service.py` and its own Chroma wrapper — retired. All Chroma access now goes through `ml.rag.retriever.HybridRetriever` exclusively, so there's one schema, one embedding model (MedCPT, not Chroma's default), one collection.
- `backend/app/services/timeline_builder.py` (Postgres-backed) — replaced by `graph_reader.py` (Neo4j-backed).
- Postgres `observations` and `evidence_passages` tables — dropped. They duplicated data `ml/graph` and `ml/rag/retriever` already own, with a weaker extractor behind them. See the new Alembic migration (`f6e579764c5c`) for the exact diff.
- `patient_id` — dropped from every table, route, and Pydantic model.

## 5. Fixes made along the way

- **`is_outbound_host_allowed()` prefix-bypass bug** (`app/security.py`): used `host.startswith(prefix)`, which `"localhost.attacker.example"` satisfies while resolving to a remote host — the same bug class `ml/local_only.py` was written to close. Fixed to parse the actual hostname via `urlparse`.
- **Stale `medgemma:8b-q4_0` default** everywhere (config, both `.env.example`s, both `docker-compose.yml`s) — MedGemma only ships 4B/27B. Fixed to `medgemma:4b`, matching `ml/llm/ollama_client.py`'s actual default.
- **`EvidenceCitation.evidence_passage_id`/`document_id` typed as `UUID`** — real `ml/` `Chunk.id` values are source-derived strings (`patient_doc_<hash>_0`), not UUIDs. Changed to `str`.
- **`chroma_persist_dir` default was cwd-relative** (`"./data/chroma"`) — silently diverges from `ml/rag/retriever.py`'s own repo-root-relative default depending on which directory either process is launched from. Fixed to resolve from the repo root, matching `ml/`'s own convention exactly (verified live: this is the fix that made backend and `ml/` share one physical Chroma store instead of two).
- **`ml/` wasn't importable from a local (non-Docker) backend process** — `ml/` lives at the repo root, not under `backend/`; Docker's bind mount (`../ml:/app/ml`, `WORKDIR /app`) puts it on the path automatically, but `scripts/run_backend.sh` (which `cd`s into `backend/`) didn't. Fixed by exporting `PYTHONPATH` to the repo root in that script. **Verified live**: every `ml/`-backed route silently 500'd with `ModuleNotFoundError` before this fix.
- **Docker image never installed `ml/`'s dependencies** (torch, transformers, neo4j driver, etc.) — the build context was `backend/` only. Changed both compose files' backend build context to the repo root and `docker/Dockerfile.backend` to install both `backend/requirements.txt` and `ml/requirements.txt`. `ml/`'s *source* still isn't baked into the image — it's still bind-mounted read-only at runtime, so editing `ml/` locally doesn't require an image rebuild.
- **Ollama/Neo4j unreachable from inside a bridge-network Docker container** — `ml.llm.ollama_client.OllamaClient` and `ml.graph.client.GraphClient` both call `ml.local_only.require_localhost()`, which only accepts a URI whose hostname is *literally* `localhost`/`127.0.0.1`/`::1` — a bridge-network service name like `ollama` or `neo4j` fails that check (correctly — it's closing a real privacy-boundary bug, not an arbitrary restriction). Fixed by setting the `backend` service to `network_mode: host` in both `docker-compose.yml`s, so every other service's *published* port is reachable at `localhost` from inside the backend container, without touching `ml/`'s code. **Caveat**: host networking is Linux-native; Docker Desktop (Mac/Windows) only has a beta opt-in for it (4.29+). See §8.

## 6. Known gaps / honest limitations

- **`ml/rag/retriever.py`'s in-memory chunk cache can go stale relative to Chroma** if a *separate process* (e.g. `ml/rag/ingest/run_ingest.py`, run standalone to seed reference sources) writes to the same Chroma store while the backend is already running — `HybridRetriever.retrieve()` will `KeyError` on an id it doesn't have cached. Found live during testing (see §7). Not a bug in backend's wiring — it's a real gap in `ml/`'s single-process cache-invalidation design, out of scope to fix here since it's `ml/`'s file. Mitigation: restart the backend after running any standalone ingestion script.
- **Deterministic table extraction & prose LLM extraction replaced by `datalab-to/lift`**:
  Previously, deterministic table extraction only recognized olmOCR HTML tables while text PDFs required a separate `qwen3.5:9b` LLM pass. Both are now replaced by unified schema-guided extraction via `datalab-to/lift` (9.7B VLM), which extracts observations, reference ranges, flags, medications, and conditions directly into structured JSON in a single pass.
- **`LIFT_MODEL`, `LIFT_DEVICE`, and `PHIRE_MOCK_LIFT` configuration**:
  Backend `Settings` now exposes `lift_model`, `lift_device` (`"auto"`, `"cuda"`, `"cpu"`), and `phire_mock_lift` (for offline fast tests), plumbed into `ml_singletons.get_lift_extractor()`.
- ~~**`ClaimVerifier.verify()` ran one NLI forward pass per evidence chunk**~~ — batched in `[0.7.4]` (token-budget batching; see `CHANGELOG.md`). Measured gain is modest: ~1.0× on a typical turn, ~2–3× on a worst-case pool, because time is dominated by the long 512-token passages, which are compute-bound.
- **`ml/graph/document_dates.py` falls back to today's date when no clinical date can be extracted from a document** — a deliberate, documented tradeoff ("undated is worse than mis-dated for a time-series graph"), reaffirmed during the review pass rather than reversed. Can make an old, undated document look like the most recent reading in trend calculations; if this bites in practice, revisit by deciding what "unknown date" should mean downstream (skip the observation? exclude from trends only?) rather than just removing the fallback.
- **`ObservationType.SYMPTOM`/`VITAL`** have no dedicated node label in `ml/graph`'s schema (everything numeric is `:Observation`) — filtering to either returns an empty list, not an error.

Frontend work starts from `docs/FRONTEND_HANDOFF.md` and `docs/API_REFERENCE.md`, generated from this handoff's state — see those instead of treating "no frontend yet" as still true.

Resolved in the review pass after this handoff (see `CHANGELOG.md`'s `[0.4.0]`): the `claims` table now gets real rows from `router_chat.py`; a `GPU_LOCK` in `ml_singletons.py` serialized chat generation against document ingestion (superseded by the GPU modes in §9); the `nginx` proxy profile now runs host-networked like `backend` so it can actually reach it.

## 7. Testing performed

All of the following were run against **real** infrastructure — a fresh Postgres 16 + pgvector container, a fresh Neo4j 5 container, and PHIRE's own Ollama instance with the real `medgemma:4b` and `qwen3.5:9b` models pulled (not mocks, not the fallback stub path):

1. **Schema**: Ran `alembic upgrade head` against a blank Postgres, then `alembic revision --autogenerate` to capture the exact diff to the new single-patient schema, applied it, and inspected the resulting tables via `psql \d` — matches the SQLAlchemy models exactly.
2. **App assembly**: Imported `app.main:app` and confirmed all 8 routers + `/openapi.json` build without error (14 routes registered, schema valid).
3. **Health check**: `POST /api/health` → `{"status":"ok","database":true,"ollama":true,"vector_store":true,"graph":true}` — all four real dependencies verified live.
4. **Document upload → real ingestion**: Uploaded a real PDF (generated via PyMuPDF) through `POST /api/documents/upload`. Verified via `GET /api/documents/{id}` that status reached `processed`, and that:
   - Chunks were correctly indexed (found via `GET /api/search/evidence`, real MedCPT + BM25 hybrid retrieval).
   - Prose LLM extraction (`qwen3.5:9b`) correctly pulled all three lab values, a medication (`metformin 500mg twice daily`, status `continued`), and a condition (`type 2 diabetes`, status `active`) into Neo4j — verified via `GET /api/observations` and `GET /api/timeline`.
5. **Real chat, end-to-end**: `POST /api/chat` with `"What was my most recent LDL cholesterol level and is it high?"` against seeded trend data (two LDL readings a year apart) plus the uploaded document returned:
   ```json
   {"answer":"My most recent LDL cholesterol level was 162 mg/dL 162 mg/dL is considered high",
    "claims":[
      {"statement":"My most recent LDL cholesterol level was 162 mg/dL","status":"DERIVED","confidence":0.866},
      {"statement":"162 mg/dL is considered high","status":"SUPPORTED","confidence":0.788,"source_filename":"labs.pdf","source_span":[0,100]}
    ]}
   ```
   Correct on every axis: `DERIVED` for the claim that matched a precomputed trend fact, `SUPPORTED` with an exact source citation for the claim backed by the uploaded document, real confidence scores from real NLI probabilities — not fixture data, not a mock.
6. **`POST /api/claims/extract`**: Real `qwen3.5:9b`-backed extraction correctly decomposed a two-sentence answer into 4 atomic claims.
7. **`POST /api/evidence/verify`**: Correctly returned `SUPPORTED`, confidence `0.996`, with the right source citation.
8. **`GET /api/recommendations/fitness`**: Correctly `501` (matches `ml/recommendations`' actual stub-only state).
9. **Persistence**: Verified `chat_messages` and `audit_log` rows via direct `psql` queries — both correctly populated by real requests.
10. **Cleanup**: All test containers torn down; the other project's Ollama container (temporarily stopped, with explicit permission, to free port 11434 for the real model pulls) was restarted and confirmed healthy afterward.

No test suite (pytest) existed in the repo before this pass and none was added — every check above was a live integration test against real infrastructure rather than mocks, which is a stronger correctness signal for this specific integration risk (the whole point was verifying `ml/`'s *actual* interface, not a guessed one) but doesn't replace having fast, repeatable unit tests. Worth adding a pytest suite as a follow-up, using this session's manual test sequence as the basis for fixtures.

### 7.1 Second pass: redundancy/efficiency review + regression + edge-case testing

A follow-up review pass re-read every changed file specifically looking for duplication, dead code, and inefficiency, then re-ran the integration tests against fresh containers to confirm nothing broke. Found and fixed:

- **Duplicated citation-building logic** in `router_search.py` and `router_evidence.py` (identical `Chunk` → `EvidenceCitation` mapping in both) — extracted into `app/services/citations.py`.
- **Dead Pydantic field**: `EvidenceVerifyRequest.evidence_passage_ids` was declared but never read anywhere (by design — `/verify` re-retrieves its own evidence from the claim text). Removed.
- **Unused dependencies in `backend/requirements.txt`**: `pymupdf`, `pytesseract`, `pillow`, `chromadb` were left over from the retired standalone document/embedding pipeline. Grep-confirmed zero direct imports anywhere in `backend/app/` (all Chroma/OCR access now goes through `ml/` exclusively). Removed from both `backend/requirements.txt` and the `tesseract-ocr` apt package in both Dockerfiles.
- **Redundant migration history**: the two-migration chain (create the old `patient_id`-scoped schema, then immediately alter it away) was collapsed into one clean init migration, since neither had ever been applied to a real/shared database. Verified with `alembic check` that it produces **zero drift** from the current models, plus a full upgrade → downgrade → re-upgrade cycle against a blank Postgres.
- **Inconsistent import style**: `router_health.py` imported `ml_singletons` functions inline inside `try` blocks while every other router imports them at module level (safe to do — `ml_singletons.py` only imports `ml/` lazily inside its own functions). Hoisted for consistency.

Regression + new edge-case tests run against fresh Postgres/Neo4j containers after these fixes:

- Health check, document upload → processing → search, evidence retrieve/verify — all re-verified working after the refactors (real MedCPT retrieval, real BART-large-MNLI verification).
- **Error paths**, none previously tested: invalid file type → `415`, oversized upload → `413`, nonexistent document → `404`, malformed chat request → `422`, missing required query param → `422` — all correct.
- **Neo4j-outage behavior for `/api/chat`**: stopped Neo4j mid-session → clean `502` with a clear error message (not a crash/hang), confirming the fail-request design decision (§ "known gaps") actually behaves as documented. Restarted Neo4j and retried on the **same running backend process** (no restart) — the QAChain's long-lived `GraphClient` driver recovered automatically and produced a correct, evidence-cited answer, confirming the Neo4j driver's built-in reconnection works across an outage.
- **Partial-failure persistence**: confirmed the user's chat message is still saved even when the assistant turn fails (e.g. during the Neo4j outage above) — matches the original design intent.
- `docker compose config` validated both compose files parse correctly; `pip check` confirmed no dependency conflicts between `backend/requirements.txt` and `ml/requirements.txt` installed together.

All test infrastructure (containers, volumes, temp files) was torn down afterward; the repo is in the same state it would be in for a fresh clone.

## 8. How to run it

**Local (no Docker) — recommended for development:**
```bash
scripts/setup.sh          # venv + backend/requirements.txt + ml/requirements.txt + npm install
# fill in backend/.env: DATABASE_URL, OLLAMA_HOST/MODEL, NEO4J_URI/USER/PASSWORD, CHROMA_PERSIST_DIR
# have Postgres, Neo4j, and Ollama reachable at those addresses (docker run, or scripts/run.sh's individual services)
ollama pull medgemma:4b       # the only Ollama model the app uses (extraction is lift, in-process)
scripts/run_backend.sh     # alembic upgrade head + uvicorn --reload, PYTHONPATH set to repo root
```

**Docker (full stack):**
```bash
scripts/run.sh              # creates .env / backend/.env if missing, detects an NVIDIA runtime (adds
                            # docker/docker-compose.gpu.yml), builds, starts, waits until the backend is healthy
scripts/run.sh down         # stop (data volumes and the repo's data/ are kept)

# one-time: seed the public reference corpus (MedlinePlus/PubMed/USDA; needs network)
docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.gpu.yml --profile ingest run --rm ingest
```
What `docker/docker-compose.yml` starts: `postgres`, `neo4j`, `backend` (single uvicorn worker, runs `alembic upgrade head` on every start via `docker/backend-entrypoint.sh`, healthcheck on `/api/ping`) and `frontend`. **Ollama is the one already running on the host** (`OLLAMA_HOST`, default `http://localhost:11434`; `medgemma:4b` is the only Ollama model the app uses) — no second copy of the model. Only when the host has none does `scripts/run.sh` enable the bundled container (`--profile ollama`: `ollama` + a one-shot `ollama-pull` that fetches `OLLAMA_MODEL` if missing). The `nginx` reverse proxy (`proxy`) and the reference-corpus `ingest` job are opt-in profiles.

- **Always pass `--env-file .env`.** Compose reads `.env` from the compose file's own directory (`docker/`), not the repo root, so a plain `docker compose -f docker/docker-compose.yml up` silently ignored every setting in the root `.env` (ports, passwords, model). `scripts/run.sh` does this for you.
- **GPU** is in a separate override (`docker/docker-compose.gpu.yml`) so the base file also starts on hosts without an NVIDIA runtime. It needs the NVIDIA Container Toolkit (Fedora: `sudo dnf install nvidia-container-toolkit`, `sudo nvidia-ctk runtime configure --runtime=docker`, restart Docker). Without a GPU, chat runs on CPU (slow) and document extraction with lift is not practical.
- **Privacy / network exposure.** PHIRE has no authentication, so every published port is bound to `127.0.0.1` and the backend listens on loopback (`BACKEND_HOST`). Reaching it from other machines is an explicit opt-in: the `proxy` profile (nginx, 25MB uploads, SSE-safe settings) plus `BACKEND_HOST=0.0.0.0`, on a network you trust. For same-origin calls through the proxy, build the frontend with `NEXT_PUBLIC_API_URL=` (empty).
- **`NEXT_PUBLIC_API_URL` is a build argument** (Next.js inlines it into the bundle at `next build`); changing it needs `--build`. `CORS_ORIGINS` is derived from `FRONTEND_PORT`.
- **Data.** `PHIRE_DATA_DIR` (default the repo's `data/`) is bind-mounted at `/app/data`: uploads, Chroma (including the reference corpus), the audit log and the ingest manifest, shared with a local run. `HF_CACHE_DIR` (default a named volume) holds Hugging Face weights — lift alone is 18GB, so point it at an existing `~/.cache/huggingface` to avoid re-downloading; `OLLAMA_MODELS_DIR` likewise. The backend container runs as non-root `PHIRE_UID:PHIRE_GID` (default 1000) so files in `data/` stay yours.
- **Python 3.12** in the backend image: `lift-pdf` requires >= 3.12 (the previous 3.11 image could not install it at all).
- **`ml/` is baked into the image** (copied after the dependency layer, so editing it rebuilds only tiny layers). It used to be bind-mounted from the checkout, but on SELinux hosts (Fedora/RHEL) the container could not read that mount at all ("Permission denied"). The remaining bind mounts (data dir, optional host HF cache) carry `:z` for the same reason.
- **Cold-start concurrency is handled.** `preload_ml_modules()` imports `ml/`'s heavy modules once at startup (a lifespan hook), and the failure rollback takes the GPU lock before touching the retriever. Before this, uploading a document and chatting within the first minute of a cold container failed (`cannot import name 'AutoModel' from 'transformers'` and Chroma `KeyError`) — reproduced in Docker, fixed, and re-verified.
- **nginx** (`proxy` profile) is a template (`docker/nginx.conf.template`): it follows `BACKEND_PORT` / `FRONTEND_PORT` and listens on `PROXY_PORT` (default 8080). It allows 25MB uploads (nginx's 1MB default returned 413 for every real PDF) and passes SSE through unbuffered.
- **There is no standalone backend image.** The backend cannot start without `ml/`; the old ml/-free `Dockerfile.backend.standalone` crashed on `import ml` and was removed.
- Note: `backend` runs with `network_mode: host` (see §5) — on Docker Desktop for Mac/Windows this needs the beta host-networking opt-in (Docker Desktop 4.29+, Settings → Resources → Network); on Linux it works natively. Without it, backend can't reach Ollama/Neo4j and every `ml/`-backed route will fail.

**Verify it's working:**
```bash
curl -X POST http://localhost:8000/api/health
# {"status":"ok","database":true,"ollama":true,"vector_store":true,"graph":true}
```
If `vector_store`/`graph` are `false`, check `detail` in the response — almost always either `ml/` isn't importable (PYTHONPATH, or Docker network mode) or Neo4j/Ollama isn't reachable at the configured URI.

## 9. GPU modes and SSE progress (added 2026-10-04)

### 9.1 Two GPU residency modes — `app/services/gpu_modes.py`

On the 8GB dev GPU, quantized lift (~6.5GiB peak) cannot coexist with the chat-time models, so the backend keeps exactly one of two **groups** resident:

| Mode | Resident on GPU | Measured |
|---|---|---|
| `LIFT` | `datalab-to/lift` (4-bit NF4) only | ~6.5GiB peak while extracting |
| `CHAT` | MedCPT query+article encoders, cross-encoder reranker, BART-large-MNLI, Ollama's `medgemma:4b` | ~6.9GB total (Ollama gets ~2.3 of its 3.5GiB on-GPU) |

`gpu_mode(mode, on_progress=None)` is a context manager that **replaces the bare `GPU_LOCK`** at every call site (`router_chat`, `router_claims`, `router_evidence` ×2, `router_search`, `document_processor`). It takes the process-wide lock, and — only if the mode *changed* — evicts the other group: entering `LIFT` unloads Ollama's model (`keep_alive: 0` via its API) and moves the in-process chat models to CPU RAM (`move_to("cpu")`, ~1s to bring back); entering `CHAT` releases lift and moves them back to CUDA. Requesting the mode that is already active is a no-op, so consecutive chats never swap (warm chat ≈ 5.6s; the first chat after an upload ≈ 15s for the reload). Singletons not yet built are never constructed just to be moved.

`document_processor.process_document` therefore runs extraction under `gpu_mode(LIFT)` and embedding/indexing under `gpu_mode(CHAT)`. `LiftExtractor` additionally frees its own weights after every document (`_release_model`).

### 9.2 SSE endpoints and the progress channel

- `POST /api/chat/stream` — `router_chat.run_chat()` is now the shared turn implementation behind both `POST /api/chat` and this endpoint. The stream runs the turn on its own thread with its own `SessionLocal()` (the request-scoped `get_db` session is closed before a streaming body finishes) and passes events through a `queue.Queue`.
- `GET /api/documents/{id}/events` — backed by `app/services/progress.py`, an in-memory per-document event list + `threading.Condition`. `process_document` publishes stages; subscribers get history replayed then live events; `upload`/`/process` call `progress.reset()` first. Single-process only (matches the single-user deployment); history is lost on restart, in which case the endpoint emits one event with the stored DB status.
- Frame formats and stage lists: [API_REFERENCE.md](API_REFERENCE.md).
- `ml/chains/qa_chain.py`'s `QAChain.answer()` takes an optional `on_progress(stage, message)` callback that the chat stream feeds; it never affects results.

### 9.3 Running this machine's stack

Other projects on the dev box occupy ports 3000, 7474/7687 and 5433. PHIRE ran on: frontend `:3001`, backend `:8000`, Postgres `:5432`, Neo4j bolt `:7688` / http `:7475` (`NEO4J_BOLT_PORT=7688 NEO4J_HTTP_PORT=7475 docker compose -f docker/docker-compose.yml up -d postgres neo4j`), host Ollama `:11434`. Export `NEO4J_URI`/`NEO4J_PASSWORD` for the backend and for `ml/` tests that touch Neo4j. Backend dependencies were installed into `ml/.venv` (single shared environment) rather than a second multi-GB torch venv. Add the frontend origin to `CORS_ORIGINS`.
