# Extraction & Chat Pipeline Changes — Sept 2026

Owner: Anika — Backend Infrastructure. This documents a round of fixes to document extraction and the chat/verification pipeline, done against a real local dev setup (Postgres + Neo4j via Docker, native `ollama serve` for GPU access, real Gemini API). Read this before touching `ml/rag/ingest/`, `ml/chains/qa_chain.py`, `ml/claims/`, or the chat-related backend routes.

## 1. Why this happened

Two problems, discovered in this order while testing on a MacBook (Apple Silicon, no CUDA):

1. **Document extraction barely worked.** The existing `datalab-to/lift` VLM path (`ml/rag/ingest/lift_extractor.py`) had no working Apple GPU path (only checked `torch.cuda.is_available()`), so it either silently ran in `PHIRE_MOCK_LIFT` mode (returning the same 3 canned fake observations regardless of the uploaded file) or, when forced to run for real, took many minutes per document on CPU.
2. **Chat answers were unreliable even with real data**, defaulting to "I don't have enough verified evidence" far more than expected, or (for broad questions) narrating the patient's entire unrelated lab panel instead of answering the question, or hanging/crashing outright.

Both got root-caused and fixed rather than papered over. Section 2 covers extraction, section 3 covers chat.

## 2. Document extraction: Lift VLM → Gemini vision pipeline

**`ml/rag/ingest/lift_extractor.py` is no longer the active extractor.** It's left in place (untouched) but nothing calls it anymore.

**New: `ml/rag/ingest/gemini_extractor.py`** — cloud vision-LLM extraction via Gemini (`google-genai` SDK). Layout-agnostic: PDF pages are rasterized with PyMuPDF to ~150 DPI PNGs, images are used as-is.

- **Two model calls per document** (not per page): an extraction pass, then a verification pass that audits the first pass against the same page images and can only correct/remove markers — never invent new ones (enforced server-side by intersecting marker names, not just by prompt instruction).
- Extraction schema captures `name`, `value`, `unit`, **and now also `reference_range` and `interpretation`** if the report prints them (most lab reports do — a printed "High"/"Low" flag or a "70–100" range). This was the single biggest lever on chat answer quality — see §3.1.
- Also extracts `medications`, `conditions`, and `document_date` in the same call, so the rest of the pipeline (`ml/graph/*`, `document_processor.py`) needed **no changes** — output is still shaped to `ml.rag.ingest.lift_schema.CLINICAL_DOCUMENT_SCHEMA`.
- **Known Gemini quirk, fixed generically**: it sometimes double-escapes a unicode character in its JSON output (writes the literal text `µ` instead of `µ`, or occasionally drops the hex digits entirely, producing an unrecoverable bare `\u`). This is valid JSON — `json.loads` has nothing to reject — but the literal backslash sitting in the string later breaks a *second*, unrelated JSON parse downstream (`ml/claims/extractor.py` re-parses LLM output that may quote this text back), which was silently zeroing out every extracted claim for an otherwise-correct answer. Fixed in two places: `_fix_double_escaped_unicode()` in `gemini_extractor.py` (decodes well-formed escapes, strips malformed ones) and the same fix applied in `ml/claims/extractor.py._parse_claims` as defense-in-depth, since a local model's own JSON output could hit the same failure mode independently.
- Retry logic covers `RESOURCE_EXHAUSTED`/`429` (rate limit) and `UNAVAILABLE`/`503` (transient overload) — 3 attempts, honoring the server's suggested retry delay when present.

**Config**: `GEMINI_API_KEY` (required — extraction raises a clear `RuntimeError` if unset, doesn't silently fall back to mock) and `GEMINI_MODEL` (default `gemini-2.5-flash`) in `backend/.env` / `app/config.py`. `PHIRE_MOCK_LIFT=true` still works for fast local dev (returns a fixed 6-field payload, doesn't touch the network).

**Dead code left in the tree**: `ml/rag/ingest/vision_extractor.py` (a local Ollama-vision-model attempt that predated the Gemini switch — Ollama on Docker has no Metal passthrough on macOS and crashed on vision input; a native `ollama serve` instance worked but was far slower than Gemini for this). Not wired to anything; safe to delete, kept only because it wasn't asked to be removed.

## 3. Chat pipeline (`ml/chains/qa_chain.py`, `ml/claims/`, `ml/graph/`)

### 3.1 Root cause of "not enough evidence" / low-confidence answers

`ml/claims/verifier.py` verifies a claim by NLI **entailment** against a pool of evidence chunks — it can confirm "this text restates that text," not "4.74 < 5.7." A claim like *"HbA1c is within the normal range"* has nothing to entail against unless the exact comparison already exists as text somewhere in the pool.

Two fixes, same underlying idea as the trend-fact mechanism that already existed:

- **`ml/graph/reference_ranges.py`** (new) — standard published reference ranges (MedlinePlus/NIH) for the lab markers this app already has reference literature for (`ml/rag/ingest/topics.py`'s labs subset: HbA1c, TSH, LDL/HDL/Triglycerides, Glucose, Vitamin D/B12, Uric Acid, Potassium). `classify(value, range)` does the actual arithmetic in Python — exact and deterministic, not left for the LLM or NLI.
- **`ml/graph/patient_context.py:get_reference_range_facts()`** (new) — for each current observation, if the source document *didn't* already print its own `reference_range`/`interpretation` (which always takes precedence), computes one from the table above and emits a sentence like `"HbA1c of 4.74% is within the normal range (standard reference range: below 5.7% normal, ...)."`. Wired into `QAChain.answer()` exactly like `get_trend_facts()` — it's folded into `observations` for the generation prompt and into the `patient_derived` verification pool, so a matching claim gets relabeled `DERIVED` (not `SUPPORTED`, not NLI-gated) at full confidence.

This alone fixed most "I don't have enough evidence" cases where the report's own printed flag or a standard range should have made the answer obvious.

### 3.2 Topic short-circuit — bypasses the LLM entirely for known health topics

Even with 3.1 fixed, an open-ended question like "do I have diabetes?" against a report that *doesn't* contain glucose/HbA1c would make the LLM narrate whatever unrelated markers *were* in the panel (e.g. a full CBC breakdown) instead of just saying "not tested." Tightening the system prompt (see 3.3) helped but didn't fully fix it.

**New: `ml/graph/reference_ranges.py:TOPIC_MARKERS` / `detect_topic()`** — a small keyword table (diabetes, thyroid, cholesterol, kidney, gout, vitamin D/B12, electrolytes) mapping a topic to the marker names that actually answer it. **`ml/graph/patient_context.py:get_topic_marker_facts()`** returns `(facts, missing_markers)` for a topic — found markers get their value + classification (again preferring the report's own printed interpretation), missing ones are named explicitly.

**Wired in `backend/app/api/router_chat.py`**, before intent classification / `QAChain` entirely: if `detect_topic(question)` matches, the response is built directly from `get_topic_marker_facts()` — no LLM call, no NLI verification (every fact is `DERIVED` at confidence 1.0, since it's an exact table lookup). Typical latency: **<0.2s**, vs. 15–50s+ through the full RAG pipeline.

This only fires for the topics registered in `TOPIC_MARKERS`. Anything else (e.g. "am I anemic?" — anemia isn't registered) still goes through the full LLM pipeline. Extending coverage is just adding an entry to `TOPIC_MARKERS` + `_TOPIC_KEYWORDS`.

### 3.3 Prompt tightened to stay on-topic

`ml/llm/prompts.py:CHAT_SYSTEM_PROMPT` — added an explicit instruction that CONTEXT may contain patient facts unrelated to the question, and the model should only discuss what's relevant and say plainly when relevant data is missing, rather than substituting nearby-but-irrelevant facts. Generic (no topic-specific hardcoding); helps for any topic not covered by §3.2's short-circuit.

### 3.4 Local model device selection — CPU on Apple Silicon

`ml/claims/verifier.py`, `ml/rag/reranker.py`, `ml/rag/embeddings.py` all had `_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"` — never checked MPS, so every local model (NLI verifier, MedCPT cross-encoder reranker, MedCPT embeddings) silently ran on CPU on a Mac. All three now fall back to `mps` before `cpu`.

### 3.5 Chat generation: wrong Ollama instance, then a hang, then a masked timeout

Three separate issues here, found in sequence:

1. **Chat generation (`medgemma:4b`) was pointed at a Dockerized Ollama** (port `11434`, actually a different project's container) — Docker Desktop on macOS has no Metal/GPU passthrough, so generation ran CPU-only. Fixed by running a **native** `ollama serve` (port `11435`) and pointing `OLLAMA_HOST` at it — this reaches the host GPU directly. `medgemma:4b` needs to be pulled into *this* instance specifically (`OLLAMA_HOST=127.0.0.1:11435 ollama pull medgemma:4b`), not just the Docker one.
2. **No output-token cap.** `ml/llm/ollama_client.py:generate()` didn't set Ollama's `num_predict`, so a request with no natural stop point could run indefinitely — observed live: one request sat for a full 10 minutes before Ollama itself gave up and returned a 500. Added a `max_tokens` parameter (default 1024; `ml/claims/extractor.py` passes 400 since it only needs a short JSON list) — bounds worst-case latency instead of relying on the client-side timeout to eventually intervene.
3. **`backend/.env` had a stale `OLLAMA_TIMEOUT_SECONDS=30`** predating this work, silently overriding the more realistic default — pydantic-settings env vars win over the Python-level field default. Bumped to `240` in both `.env` and `.env.example`.
4. **Startup warm-up** (`backend/app/main.py:_warm_up_models`) — all local models (embeddings, reranker, verifier) plus one throwaway Ollama `generate()` call now happen in a background thread on FastAPI startup, so the *first* real chat message doesn't pay for every lazy `@lru_cache` singleton's cold load at once (this is what made the first message after a restart take minutes even once everything else was fixed).

## 4. `documents.report_date`

New column on `Document` (`backend/app/database/schemas.py`), migration `a1b2c3d4e5f6_add_document_report_date.py`. User-selectable at upload (`report_date` form field, `frontend/app/documents/page.tsx` date picker), defaults to today if omitted. `document_processor.py` now uses `document.report_date` — not a date guessed from the document's own text — as the single effective date for every medication/condition/observation fact this document contributes to the graph. This is what lets the AI reference a concrete, trustworthy date per report instead of an inferred one.

(Note: an earlier, unrelated migration with this same purpose existed on a different branch pre-merge and caused a schema/model mismatch after a branch switch — resolved by writing this fresh migration against current models. Not expected to recur, but if you see a duplicate-sounding migration in history, that's why.)

## 5. Frontend: per-marker trend dropdown

`frontend/app/page.tsx` — the dashboard timeline chart previously overlaid every tracked marker on one `LineChart` (unreadable once more than ~2 markers had data). Replaced with a dropdown (defaults to the first available marker) that shows one marker's trend at a time, Y-axis labeled with its unit.

`frontend/app/documents/page.tsx` also now self-heals its `localStorage` document-card cache: on load it checks every cached card against the backend and drops any whose document no longer exists, instead of requiring a manual `localStorage.clear()` after a DB reset.

## 6. Operational notes for whoever runs this next

- **Two Ollama instances matter**: Docker's (port `11434`, whatever else runs on this machine) and native (port `11435`, GPU-backed, what this app's chat/extraction-adjacent code should use). Confirm `OLLAMA_HOST` in `backend/.env` points at `11435`, and that `ollama serve` is actually running natively (`ps aux | grep "ollama serve"`) — it doesn't auto-start.
- **`GEMINI_API_KEY` must be set** for real extraction; unset it (or set `PHIRE_MOCK_LIFT=true`) for fast, network-free local dev.
- **After any manual edit to Chroma/Neo4j from outside the running backend process** (a script, a different process, `docker exec`), restart the backend. `HybridRetriever` loads its BM25 index into memory once at construction and never re-reads it; a stale Chroma file handle after an external `rm -rf` on `data/chroma` will also throw `attempt to write a readonly database` until restarted.
- **Reference corpus vs. patient data are separate concerns** when clearing test data: `ml.rag.ingest.run_ingest` populates the shared MedlinePlus/PubMed/USDA corpus (588 chunks as of this writing); wiping the whole Chroma store wipes both together. If you need to clear just uploaded documents, filter Chroma chunks by `metadata.source == "patient_document"` instead of deleting the collection.
