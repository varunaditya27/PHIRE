# PHIRE: Engineering Backlog — Known Gaps, Tech Debt, Open Design Questions

**Status**: Living document. Distinct from `docs/AGGRESSIVE_ROADMAP.md`
(feature build checklist) — this tracks things that already exist but
have a known limitation, a deferred fix, or an undecided design question,
surfaced mostly through code review and live testing rather than planned
up front. Update this as items are resolved or new ones are found; don't
let it silently go stale.

**As of**: 2026-08-28, after the `backend/` ↔ `ml/` integration + review
pass described in `CHANGELOG.md`'s `[0.4.0]`–`[0.5.0]` and
`docs/BACKEND_HANDOFF.md`.

---

## `ml/`

- **`ml/rag/ingest/patient_documents.py`'s `PDFTextExtractor` only handles
  text-based PDFs.** A scanned PDF (image-only, no embedded text layer)
  falls through uncaught today. **Design already decided, not yet
  built** — see `docs/PDF_INGESTION_ROADMAP.md` for the full reasoning
  and benchmarked approach.
- **Deterministic table extraction (`build_table_observations`) only
  recognizes olmOCR's `<table>` HTML output**, not plain pypdf-extracted
  text tables. For a text-based PDF (the common case — no OCR involved),
  lab values only reach the graph via prose LLM extraction, not the more
  reliable deterministic table path. Found live during testing
  (`docs/BACKEND_HANDOFF.md` §6).
- **`backend/.env`'s `OCR_MODEL` is silently ignored.**
  `PROSE_EXTRACTION_MODEL` was wired through in the `[0.5.0]` review pass,
  but `extract_text()`'s OCR path takes an `extractors` list, not a model
  string, and nothing constructs a custom one from config yet. Needs
  `ml/rag/ingest/patient_documents.py`'s extractor interface looked at.
- **`ml/claims/verifier.py`'s `ClaimVerifier.verify()` runs one NLI
  forward pass per evidence chunk** instead of batching, unlike
  `ml/rag/reranker.py`. Adds avoidable GPU latency to every claim
  verified (every `/api/chat` turn, every `/api/evidence/verify` call).
  Optimization, not a correctness bug.
- **`ml/rag/retriever.py`'s in-memory chunk cache can go stale relative
  to Chroma** if a separate process (e.g. `ml/rag/ingest/run_ingest.py`,
  run standalone to seed reference sources) writes to the same Chroma
  store while the backend is already running — `retrieve()` will
  `KeyError` on an id it doesn't have cached. Mitigation today: restart
  the backend after any standalone ingestion script. A real fix needs a
  cache-invalidation design (poll Chroma's own state? a write-through
  notification?), not just a patch.
- **`ml/graph/document_dates.py` falls back to today's date** when no
  clinical date can be extracted from a document — a deliberate,
  documented tradeoff ("undated is worse than mis-dated for a
  time-series graph"), reaffirmed (not reversed) during the `[0.5.0]`
  review. Can make an old, undated document look like the most recent
  reading in trend calculations. If this bites in practice, the fix
  needs a real answer to "what does an unknown date mean downstream"
  (skip the observation entirely? exclude it from trends only, but still
  show it as a fact?) — not just deleting the fallback.
- **`ObservationType.SYMPTOM`/`VITAL`** have no dedicated node label in
  the graph schema (everything numeric is `:Observation`) — filtering to
  either returns an empty list, not an error. Low-priority unless/until
  those types are actually populated.
- **Multi-hop graph-RAG retrieval** (LightRAG-style entity/relationship
  traversal at query time, for multi-hop/relational/contradiction
  questions) is planned but not implemented — see
  `docs/GRAPH_SCHEMA_ROADMAP.md` §3f and `ml/README.md`.
- **Fitness/nutrition recommendation models are stubs.**
  `ml/recommendations/` has no `recommend()` function — backend's
  `/api/recommendations/*` endpoints permanently return `501` until this
  is built. PAMAP2-based HAR model work hasn't started.
- Deferred clinical-KG schema work (ontology mapping, provenance-as-edges,
  and more) has its own trigger-condition-based backlog — see
  `docs/GRAPH_SCHEMA_ROADMAP.md`, don't duplicate it here.

## `backend/`

- **No automated test suite.** `ml/` has 189 passing pytest tests
  (`ml/tests/`); `backend/` has none — verification so far has been live
  manual integration testing (`docs/BACKEND_HANDOFF.md` §7). Worth
  building a pytest suite using that manual test sequence as the basis
  for fixtures, especially before frontend integration makes the API
  surface harder to change freely.
- **The `claims` Postgres table is written to (as of `[0.4.0]`) but
  nothing reads it yet.** It exists so claims are queryable in SQL for
  evaluation/analytics instead of parsing every `chat_messages.claims`
  JSON blob — that consumer (an evaluation script, an analytics query)
  doesn't exist yet. Likely Shashwati's `evaluation/` scope once that
  starts.
- **`nginx` proxy profile** was fixed to run host-networked (matching
  `backend`) in `[0.4.0]`, and `docker compose config` validates it, but
  it hasn't been live-tested against a real running stack end-to-end —
  worth a real smoke test before anyone actually relies on it instead of
  hitting the backend directly on `localhost:8000`.
- **Caching layer** (reduce repeat-question LLM inference latency) not
  started — `docs/AGGRESSIVE_ROADMAP.md`'s Integration + Polish phase.
- **CI/CD** not set up at all yet.

## `frontend/`

- **Nothing built yet** — `frontend/` is still the unmodified
  `create-next-app` scaffold. `docs/FRONTEND_HANDOFF.md` and
  `docs/API_REFERENCE.md` are the starting point once work begins.
- No test harness (parallel to `backend/`'s gap above).
- Chat UI with clickable evidence highlights, health timeline
  visualization, demo personas / end-to-end workflow testing — all
  `docs/AGGRESSIVE_ROADMAP.md` checklist items, none started.

## Cross-cutting / needs a team decision, not just an owner

- **ArchEHR-QA 2026 evaluation (167 expert cases) hasn't started.**
  Shashwati's scope per `REPO_STRUCTURE.md`; `evaluation/` doesn't exist
  in the repo yet. No baseline metrics (evidence attribution
  precision/recall, hallucination rate, response latency) have been
  measured yet either — needed for the research-paper angle
  (`docs/FEATURES_ALIGNED.md`'s research contributions section), not
  just as a nice-to-have.
- **Docker host networking is Linux-native; Docker Desktop (Mac/Windows)
  needs a beta opt-in (4.29+).** Fine for Varun's dev box — if any
  teammate develops on Mac/Windows, this needs a real decision (require
  the beta opt-in? support the non-Docker local-run path as the primary
  path on those platforms?), not just a caveat in the docs.
- **Wearable integration (Fitbit, Oura, Apple Health) and computer
  vision (food recognition, exercise posture)** are Month 2+ per
  `docs/AGGRESSIVE_ROADMAP.md`'s extended phases — untouched, no design
  work done yet.
