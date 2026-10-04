# PHIRE: Engineering Backlog — Known Gaps, Tech Debt, Open Design Questions

**Status**: Living document. Distinct from `docs/AGGRESSIVE_ROADMAP.md` (feature build checklist) — this
tracks things that already exist but have a known limitation, a deferred fix, or an undecided design
question. It lists only what is **open today**; everything that has been resolved is in `CHANGELOG.md`
(pointers at the bottom). Update it as items are resolved or found; don't let it silently go stale.

**As of**: 2026-10-05, after graph retrieval, the missing-date flow, the NLI/USDA fix and the CPU-only variant.

---

## 1. `frontend/`

- **No automated frontend tests** (Jest/Vitest/Playwright). The `[0.8.1]` review drove every page in real
  Chrome with `playwright-core`; turning that into a committed smoke test is the natural next step.
- **Chat**: no "clear conversation", no per-message timestamps; history stored before `[0.8.1]` still shows
  run-on answers (new answers are punctuated). Navigating away mid-answer does not abort the in-flight stream
  (no `AbortController`) — the backend turn completes and is saved, so nothing is lost.
- **Dashboard**: every reading is a line (a single-reading metric is a lone dot) and there is no date-range
  filter.
- **Search**: match scores sit near 100% when every hit is relevant — that is the cross-encoder's real output,
  not a bug, but it can look uninformative.
- **Accessibility pass not done** (the chat input has no label; the charts have no text alternative).
- **Pre-existing ESLint errors** (`any` types, unescaped quotes) remain in `app/chat`, `app/documents`,
  `app/search` and `lib/api.ts`; no new ones were introduced.

## 2. `backend/`

- **No `backend/tests/` directory.** The backend's services and HTTP endpoints are covered by tests that live
  in `ml/tests/` (document processing, date endpoint, delete, route-registration guard, GPU modes, SSE
  progress, evidence search, extractor selection), but chat, search, evidence, claims and observations have no
  router-level tests, and the two SSE endpoints were only verified live.
- **SSE progress state is in-process memory** (`app/services/progress.py`): single worker only; history is lost
  on restart (the events endpoint then emits one event with the stored DB status). A multi-worker deployment
  would need a shared channel (Redis / Postgres `LISTEN`). `gpu_modes.py` is per-process for the same reason —
  **do not raise uvicorn's worker count**.
- **No timeout or cancellation on the chat stream thread**: if the QA chain hangs, the SSE connection stays open
  until the client disconnects; the worker thread is a daemon and is not cancelled.
- **Documents ingested before extractions were saved cannot be re-dated** (`PUT /api/documents/{id}/date`
  returns 409 with guidance): delete and upload them again.
- **`claims.chat_message_id`** foreign key has no explicit index.
- **No claims analytics endpoints** (claims are queryable in SQL) and **no response caching**.
- **`nginx` proxy profile** works (3MB upload and streaming verified) but has not been load-tested.

## 3. `ml/`

- **Fitness & nutrition recommendation models are stubs** (`ml/recommendations/`); the endpoints return `501`.
- **Verifier workaround is a heuristic.** `ClaimVerifier` lets an entailing chunk beat contradictions from other
  chunks (this fixed correct patient claims being flagged `CONFLICTING` by a different metric's same-template
  fact), but it can mask a genuine conflict when another chunk entails the claim. A metric-aware pre-filter
  (match the claim's analyte to the fact's analyte before NLI) would be more principled. See
  `docs/RESEARCH_LOG.md` 2026-10-04 §2.
- **Graph retrieval limits** (`docs/GRAPH_SCHEMA_ROADMAP.md` §3f): the drug/condition → metric table in
  `ml/graph/relations.py` is small and hand-curated; there is no single traversal from the patient graph into a
  guideline passage in Chroma (the two legs are joined in the prompt); conflicts are only same-fact / same-date
  disagreements between different documents; medications carry the document's date, not a start date, so
  "relative to my medication" is a co-located timeline, not a before/after dosing analysis. Deferred with
  trigger conditions: claim→evidence graph edges, ontology alignment (RxNorm/LOINC/SNOMED), more node types.
- **Composite readings outside the registry stay as text** (`ml/graph/composite_readings.py`): e.g. orthostatic
  "supine 148/92, standing 130/80" in one value, paediatric "lb oz" weights, comparator values like `>90`. HbA1c
  in dual units is intentionally one observation. Adding a shape is one handler plus one dict entry.
- **CPU-only extraction** (`OllamaVisionExtractor`) takes ~2 minutes per page on a strong laptop-class CPU and,
  on a noisy scan, missed one medication and one diagnosis; digital PDFs (whose text layer is passed to the model)
  are its best case. `docs/CPU_SETUP.md` documents the limits.
- **Lift**: accuracy under 4-bit NF4 has only been checked on synthetic documents; each upload pays ~56s to load
  the model because its weights are freed after every document (needed to coexist with the chat models).
- **`ml/rag/retriever.py` keeps chunks in an in-memory cache**: if a separate process (e.g. `run_ingest.py`)
  writes to Chroma while the backend runs, the cache goes stale — restart the backend afterwards.
- **Reference ingestion**: the USDA free `DEMO_KEY` rate-limits almost immediately (set `USDA_API_KEY`), and
  there is no retry/backoff on PubMed/MedlinePlus/USDA calls beyond logging and skipping a failed topic.
  `python -m ml.rag.ingest.reformat_corpus` upgrades an already-seeded corpus offline.

## 4. `docker/` and infrastructure

- **Host networking is Linux-native.** macOS/Windows Docker Desktop need 4.29+ with the host-networking beta;
  `ml.local_only.require_localhost()` (the privacy guard) is why the backend is host-networked and not on a
  bridge network. Without Docker, run the stack with `scripts/run_backend.sh` / `run_frontend.sh`.
- **Image size**: GPU variant 11.1GB (PyTorch CUDA wheels + lift); CPU variant 2.7GB.
- **First start needs the network** (the Hugging Face weights download on first use: lift alone is 18GB; point
  `HF_CACHE_DIR` at an existing cache to avoid it). Ollama is the host's and its model must already be pulled
  (`scripts/run.sh` warns if not).
- **The bundled Ollama container** (`--profile ollama`, started only when the host has no Ollama) was validated
  with `docker compose config` but not run end to end; the host-Ollama path is what was exercised.
- **No automated Docker smoke test in CI** (verified by hand in `[0.8.0]` and `[0.9.0]`).
- The compose `postgres` image is plain `postgres:16`; Postgres is relational-only (Chroma is the vector store).

## 5. Cross-cutting and research

- **ArchEHR-QA 2026 evaluation (167 expert cases) not started** — `evaluation/` does not exist yet (Shashwati).
- **Single-patient architecture, no authentication** by design for a single-user local tool
  (`DEFAULT_PATIENT_ID = "self"`); every published port is bound to loopback.
- **Wearable integration and computer vision** (food recognition, posture analysis) are scheduled for Month 2+
  per `docs/FEATURES_ALIGNED.md`.

---

## Resolved (see `CHANGELOG.md` for details)

| Version | What was resolved |
|---|---|
| `[0.7.0]` | Lift's 4-bit quantization actually applied; LIFT/CHAT GPU modes; SSE progress; verifier no longer flags correct claims `CONFLICTING`; duplicate `/process` call |
| `[0.7.1]` | Search relevance `score`; original filename in claims; document delete |
| `[0.7.2]` | Document list and chat-history endpoints; blood pressure numeric; chat `citations`; patient-record claim sources |
| `[0.7.3]` | Every claim cites all its source documents; composite readings; `scripts/reset_data.py` |
| `[0.7.4]`–`[0.7.5]` | Batched claim verification; fp16 on CUDA |
| `[0.8.0]` | Docker deployment audited end to end (Python 3.12 image, env file, SELinux, migrations, GPU override, loopback ports, nginx, cold-start race, host Ollama default) |
| `[0.8.1]` | Frontend review: duplicated units, per-unit charts, latest readings, mobile layout, disclaimer, live status badge |
| `[0.9.0]` | Graph retrieval (multi-hop / longitudinal / conflicts); missing document date asked in the UI; USDA evidence as sentences and MedlinePlus spacing fixed; CPU-only variant; Ollama timeout honored; docs audit |
