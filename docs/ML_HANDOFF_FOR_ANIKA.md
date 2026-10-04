# ML Handoff: what's built in `ml/`, and what backend needs to know

**Audience**: Anika (`backend/`, `docker/`, `scripts/`). This is a snapshot
of everything implemented in `ml/` as of 2026-08-16 — what exists, how to
call it, what infrastructure it needs, and what's still missing. Written
so you can wire `backend/` to it without having to read every file in
`ml/` first.

**Status of this doc**: accurate as of the commits on `feat/ml-rag-core`
listed informally below. If `ml/` changes after this, treat this as a
starting map, not a live contract — check the actual code for anything
you're about to depend on precisely (function signatures, field names).

**Updated 2026-08-25** (§1.1, §5): graph integration (`ml/graph/`) landed
after this doc's original 2026-08-16 pass and changed `QAChain`'s cost/
lifetime contract — re-read §1.1 if you read this doc before that date.
Also this date: a live-testing pass found and fixed a real-corpus
contamination bug (§5.8) and a document-dating bug (§5.9); see
`docs/RESEARCH_LOG.md` for the full write-up if you want the "why," not
just the "what."

---

## 1. The two things you actually need to call

Almost everything else in this doc is context for these two entry points.

### 1.1 Answering a chat question — `ml.chains.qa_chain.QAChain`

```python
from ml.chains.qa_chain import QAChain

chain = QAChain()  # loads several models — construct once, reuse, not per-request
response = chain.answer("what was my LDL cholesterol result?")

response.answer   # str — the final answer, built only from verified claims
# chain.answer(question, on_progress=cb) — optional cb(stage, message) fired as each
# stage starts (graph, retrieve, generate, extract, verify×n); the backend's SSE chat
# endpoint uses it. Never affects results.
response.claims   # list[VerifiedClaim] — full audit trail, including dropped claims
# VerifiedClaim.source_filenames: list[str] — every uploaded document the claim rests on (a trend lists both readings' files);
# source_filename is its first entry.
response.evidence # list[Chunk] — the reranked passages the answer was drafted from (API `citations`)
```

`VerifiedClaim` fields: `claim: str`, `status: str` (`SUPPORTED` /
`DERIVED` / `CONFLICTING` / `UNCERTAIN` / `UNSUPPORTED` — `DERIVED` added
2026-08-25, see the graph-facts note below), `confidence: float` (0-1),
`source_url: str | None` (public reference chunks only), `source_filename:
str | None` (patient documents), `source_span: tuple[int, int] | None`
(exact character offset in the source document — `None` for facts that
aren't extracted verbatim, e.g. table rows; see §4). A claim whose
`source_url` and `source_filename` are **both** `None` was verified
against a *derived* graph fact (a trend computed across documents) or a graph fact with no recorded source document; direct patient-record facts now carry the uploaded `source_filename` (`get_current_patient_facts_with_sources`) — that's the
reliable way to tell "this patient's own recorded data" apart from a
document chunk at the same authority level, found necessary during live
testing (see `docs/RESEARCH_LOG.md` §2 for why this distinction matters
in practice).

All fields are plain Python — `dataclasses.asdict(response)` gives you a
JSON-serializable dict directly for an API response.

**Cost / lifetime contract — updated 2026-08-25, this changed since the
doc's original 2026-08-16 snapshot**: `QAChain()`'s constructor loads 4
models onto the GPU (embedding ×2, reranker, claim verifier) — this
takes a few seconds and ~2-3GB VRAM — **and** opens a `GraphClient`
(Neo4j driver) connection. Build one instance and reuse it across
requests in a long-lived process (e.g. at FastAPI app startup); don't
construct it per-request — a per-request `QAChain()` would reload all 4
models and reconnect to Neo4j on every single chat message, live-verified
to add tens of seconds of pure model-load latency per turn.

`chain.answer()` itself, per call, makes: one Ollama call (chat
generation), one Ollama call (claim extraction, inside `ClaimExtractor`),
and — unless you pass `observations=` explicitly to override the
auto-fetch — three Neo4j reads (`get_patient_facts`,
`get_current_patient_facts`, `get_trend_facts`, all against the single
`Patient {id: "self"}` node per §3). If Neo4j is unreachable at call
time, `answer()` raises (the Neo4j driver connects lazily on first query,
not at `GraphClient()` construction) — there's no graceful degradation
path today; decide at the backend layer whether a Neo4j outage should
fail the whole chat request or fall back to `observations=[]`.

Patient/trend facts pulled into claim verification are capped at 50 each
(`ml.chains.qa_chain.MAX_FACT_EVIDENCE`) — a defensive ceiling on NLI
verification cost, not a real limit at today's scale; if a chat response
ever looks like it's ignoring older patient history during verification
(as opposed to generation, which still sees full history), this cap is
why.

### 1.2 Ingesting a patient document — `ml.rag.ingest.patient_documents` & `ingest_patient_document`

```python
from pathlib import Path
from ml.rag.ingest.patient_documents import extract_document_data
from ml.rag.ingest.ingest_patient_document import build_chunks
from ml.rag.retriever import HybridRetriever

# 1. Extract structured clinical data via Lift VLM (single pass)
data = extract_document_data(Path("/path/to/uploaded/file.pdf"))  # digital PDF, scanned PDF, or image

# 2. Build Option A declarative clinical sentence chunks and index into Chroma/BM25
chunks = build_chunks(Path("/path/to/uploaded/file.pdf"), data=data, document_id="doc123")
HybridRetriever().add_documents(chunks)
```

Unified visual extraction via `datalab-to/lift` extracts structured clinical observations (with reference ranges and flags), medications, conditions, and narrative sections from both digital and scanned PDFs/images in a single pass.

Or run the CLI script directly, which handles extraction, chunking, indexing, and Neo4j graph writes:

```bash
ml/.venv/bin/python -m ml.rag.ingest.ingest_patient_document /path/to/file.pdf
```

Accepts: digital PDFs, scanned PDFs (no embedded text layer), and images (`.jpg`, `.jpeg`, `.png`, `.webp`).

---

## 2. Infrastructure this depends on

### 2.1 Ollama (LLM serving)

Production model requirement:

| Purpose | Model | Config env var |
|---|---|---|
| Chat generation | `medgemma:4b` | `OLLAMA_MODEL` |

Visual document extraction uses `datalab-to/lift` (9.7B VLM, 18GB in bf16), loaded in-process via Hugging Face with **4-bit NF4 quantization on CUDA** and a CPU fallback (`LIFT_MODEL`, `LIFT_DEVICE`, `PHIRE_MOCK_LIFT`). Measured on the 8GB RTX 5050: ~56s to load, ~6GiB resident, 6.5GiB peak, ~37s to extract a one-page lab report, all values correct.

**How quantization is actually applied (important):** lift's `InferenceManager.__init__` accepts *only* `method` — it silently ignores/rejects `quantization_config`/`device` kwargs and always loads bf16. `LiftExtractor._get_model()` therefore builds the NF4 model itself with `AutoModelForImageTextToText.from_pretrained(..., quantization_config=BitsAndBytesConfig(load_in_4bit, nf4, double-quant, bf16 compute, llm_int8_skip_modules=["visual"]), device_map={"": 0})`, then injects it into an `InferenceManager(method="vllm")` (which skips lift's own loader) by setting `.method="hf"` and `.model`. An earlier version passed the kwargs to `InferenceManager` inside `try/except TypeError` and silently fell back to the unquantized bf16 load, which spilled the model into CPU RAM; there is deliberately **no such fallback now** — a failed 4-bit load raises. The vision tower stays bf16. `PHIRE_MOCK_LIFT` is read at call time, and `LiftExtractor` frees its weights after every document (`_release_model`).


All benchmarked, not guessed — see `ml/claims/experiments/RESULTS.md`
(model choices generally), `ml/rag/ingest/experiments/RESULTS.md` (OCR),
`ml/graph/experiments/RESULTS.md` (prose extraction). `OLLAMA_HOST`
(default `http://localhost:11434`) must resolve to localhost — every
Ollama-calling module in `ml/` hard-rejects a non-loopback host at
construction time as a privacy-boundary enforcement, not just convention.
This check (`ml/local_only.py`, shared by the Ollama client, OCR client,
and Neo4j client) parses the URI's actual hostname rather than doing a
substring/prefix check on the raw string — so `NEO4J_URI` and
`OLLAMA_HOST` are held to the same rule; don't relax either independently.

**Note on `docs/AGGRESSIVE_ROADMAP.md`/`README.md` mentioning MedGemma
1.5**: the actual pulled/tested model is `medgemma:4b` (MedGemma is only
released in 4B and 27B sizes by Google — the docs' originally-referenced
"8b-q4_0" tag doesn't exist). If you're setting up Ollama serving from
scratch, pull `medgemma:4b`, not whatever the older docs say.

### 2.2 Neo4j (new — not yet in your docker-compose.yml)

This is genuinely new infrastructure you don't have yet. `ml/graph/`
writes structured patient facts (labs, medications, conditions) here.
Currently running as a **standalone dev container**, not part of any
docker-compose setup:

```bash
podman run -d --name phire-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/<password> \
  -v phire-neo4j-data:/data \
  docker.io/library/neo4j:5-community
```

(`docker run` with the same flags works identically if you're using
Docker instead of podman.) You'll want to fold this into
`docker/docker-compose.yml` properly rather than leave it as a manual
container — this was stood up for development, not deployment.

Config via `NEO4J_URI` (default `bolt://localhost:7687`), `NEO4J_USER`,
`NEO4J_PASSWORD` — see `ml/graph/client.py`. Same localhost-only
enforcement as Ollama.

### 2.3 Chroma

No change from what you already know — in-process, `data/chroma/` on
disk, no separate service. `data/` is gitignored (regenerable via the
ingestion scripts, not source).

### 2.4 Python environment

`ml/.venv`, Python 3.12, managed via `uv`. `ml/requirements.txt` has
everything pinned. `ml/.env.example` → copy to `ml/.env` for local
secrets (USDA/NCBI API keys, Neo4j credentials) — never commit `ml/.env`.

---

## 3. The graph schema (relevant to your Week 2 "health timeline" task)

This might directly solve a problem you already have on your list.
`ml/graph/` already builds a structured, queryable timeline of a
patient's labs, medications, and conditions — you may not need to build
timeline construction from scratch against Postgres.

```
(:Patient {id: "self"})
   ├─[:HAS_OBSERVATION]→ (:Observation {code, value, unit, reference_range, interpretation, effective})
   ├─[:HAS_MEDICATION]→  (:Medication  {code, dosage, frequency, status, effective})
   └─[:HAS_CONDITION]→   (:Condition   {code, status, effective})
        (each also: -[:FROM_DOCUMENT]→ (:Document {id, filename}))
```

Field names are FHIR-inspired (`code`/`value`/`effective`/`interpretation`)
on purpose — not full FHIR resource modeling, just the vocabulary, in
case interoperability matters later.

**`Patient {id: "self"}` is a single well-known node.** There is no
multi-patient isolation anywhere in this graph, or in Chroma's metadata,
or in the retriever's query path — PHIRE currently assumes one instance
per person. If multi-tenancy is ever a real requirement on your side,
that's a cross-cutting change needed in both `ml/graph/` and
`ml/rag/retriever.py`, not something to bolt on to just one side.

Example query (Cypher) — "what's this patient's LDL trend":

```python
from ml.graph.client import GraphClient

with GraphClient() as client:
    rows = client.run(
        "MATCH (p:Patient {id: $pid})-[:HAS_OBSERVATION]->(o:Observation) "
        "WHERE o.code CONTAINS 'LDL' RETURN o.value, o.effective ORDER BY o.effective",
        pid="self",
    )
```

`status` on Medication/Condition is one of `started`/`continued`/
`discontinued`/`unspecified` (medications) or `active`/`resolved`/
`historical`/`unspecified` (conditions) — extracted by the LLM, not
guaranteed perfectly accurate (see §6).

---

## 4. Evidence citation (`source_span`)

Every `VerifiedClaim` (and every `Chunk` in `ml/rag/retriever.py`,
metadata keys `char_start`/`char_end`) carries the exact character offset
into its source document where the evidence came from — for building an
"exact source highlighting" UI feature (this is Feature 7 in
`docs/FEATURES_ALIGNED.md`, previously unimplemented, now has the data
plumbing in place). Not populated for every chunk: table-derived facts
(a lab value pulled from an HTML table) are reformatted, not extracted
verbatim, so they have no single matching span — `source_span` is `None`
in that case, not a wrong guess. Check for `None` before using it.

---

## 5. Known limitations / things that will bite you if assumed away

1. **GPU memory: two mutually exclusive modes.** On an 8GB GPU, quantized
   Lift (6.5GiB peak) cannot coexist with MedCPT ×2, the reranker, BART and
   Ollama's chat model (~6.9GB together). The backend's
   `app/services/gpu_modes.py` keeps either the `LIFT` group or the `CHAT`
   group resident and swaps on change (see `docs/BACKEND_HANDOFF.md` §9).
   To support this, `EmbeddingModel`, `Reranker`, `ClaimVerifier` and
   `HybridRetriever` each expose `move_to(device)` (weights parked in CPU RAM,
   ~1s to restore) and track their device per instance instead of the old
   module-level `_DEVICE`. On CPU/non-CUDA setups Lift loads through lift's
   default loader with `TORCH_DEVICE="cpu"`, no quantization.
2. **INFERRED is not implemented; DERIVED is, one layer up.**
   `ClaimVerifier` itself only returns `SUPPORTED`/`CONFLICTING`/`UNCERTAIN`/
   `UNSUPPORTED`; `QAChain` relabels a SUPPORTED match against a precomputed
   graph trend sentence as `DERIVED`. A claim needing multi-hop reasoning
   still falls into `UNCERTAIN` — documented gap, not a bug.
   **Verifier selection rule (changed 2026-10-04):** if any evidence chunk
   entails the claim (≥ `ENTAILMENT_THRESHOLD`), the strongest entailing
   chunk decides the verdict; only otherwise does the chunk with the
   strongest entailment-or-contradiction signal decide. Reason: BART-MNLI
   gives ~1.0 "contradiction" between same-template sentences about
   *different* facts (an HDL value vs an LDL claim), which used to outrank
   the true 0.99-entailing fact and flip correct patient-record claims to
   `CONFLICTING`. Trade-off: a claim that is entailed by one chunk but
   genuinely contradicted by another now reports SUPPORTED.
3. **Scanned PDFs and image-based documents are fully supported** —
   `datalab-to/lift` visual extraction natively processes scanned PDFs,
   photos, and digital PDFs alike into unified structured schema output.
4. **The cross-encoder reranker is sensitive to phrasing** in ways that
   might surprise you: "what was my LDL cholesterol result?" and "What is
   my LDL cholesterol result?" (same meaning) scored measurably
   differently in testing. A patient-document floor (`ml/rag/reranker.py`)
   compensates for the worst case of this, but if you're building
   anything that assumes consistent relevance scoring across paraphrased
   queries, don't.
5. **USDA ingestion needs a real API key** (`USDA_API_KEY`) — the free
   `DEMO_KEY` default hits its rate limit almost immediately (confirmed
   live, not just documented).
6. **No retry/backoff on external API calls** (PubMed, MedlinePlus, USDA)
   beyond what's already in `ml/rag/ingest/run_ingest.py` (per-topic
   failure is logged and skipped, not retried).
7. **Document extraction validation.** Lift VLM outputs are validated
   against `CLINICAL_DOCUMENT_SCHEMA` via `validate_lift_payload()`
   (`ml/rag/ingest/lift_schema.py`). Missing or non-dict items are
   sanitized to empty lists rather than crashing ingestion. If a document
   contains no extractable clinical entities, observations, medications,
   and conditions simply return empty.
8. **Keep `data/chroma` free of test/eval fixture documents.** Found live
   2026-08-25: benchmark ingestion runs (OCR/reranker experiments) had
   left 21 chunks from a synthetic "R. Thompson" patient permanently
   indexed in the real Chroma store at `source: patient_document,
   authority: 1.0` — the same authority tier as genuine patient data, so
   they were retrievable and citable in real chat answers, and could
   cause `ClaimVerifier` to pick a same-topic decoy chunk over the real
   patient's own graph fact when both were "informative," producing a
   spurious `CONFLICTING` verdict on a true claim. Removed (backed up
   first). If you build an ingestion/eval harness that indexes into the
   real `data/chroma` for testing, delete what you add afterward — Chroma
   doesn't distinguish "real" from "test" data on its own, and there's no
   automatic cleanup.
9. **Document dates: day-first (DD/MM/YYYY), not US month-first, and DOB
   is deliberately excluded.** `ml/graph/observations.py`'s
   `find_document_date` parses ambiguous numeric dates day-first —
   PHIRE's primary audience is Indian users/clinics, where that's the
   normal convention, so `"03/01/2026"` means 3 January, not March 1st.
   It also explicitly skips any date immediately labeled `DOB`/`Date of
   Birth` — found live 2026-08-25 that a document listing DOB before its
   own service date (a realistic layout: demographics header, then visit
   details) silently misdated every Observation from that document to
   the patient's birth year under the original first-ISO-match
   implementation. If you write any date-parsing of your own against
   patient-uploaded documents, use the same day-first + DOB-exclusion
   convention for consistency, or better, reuse this function.

---

## 6. Where to look for "why was this model/approach chosen"

Every non-trivial model or library choice in `ml/` was benchmarked, not
assumed — if you need to understand *why* something works the way it
does (or want to challenge a choice), these are the primary sources, not
this doc:

- `ml/rag/experiments/RESULTS.md` — embedding model (MedCPT)
- `ml/claims/experiments/RESULTS.md` — claim verification NLI model (BART-large-MNLI)
- `ml/rag/ingest/experiments/RESULTS.md` — historical OCR benchmark (olmOCR-v2, superseded by `datalab-to/lift`)
- `ml/graph/experiments/RESULTS.md` — historical prose extraction benchmark (HandRolled + qwen3.5:9b, superseded by `datalab-to/lift`)
- `ml/rag/reranker_experiments/RESULTS.md` — reranker weight tuning + the patient-document floor fix
- `docs/GRAPH_SCHEMA_ROADMAP.md` — what's deliberately deferred in the graph schema, and the trigger condition for each


## 6. Composite readings (added 2026-10-04)

`ml/graph/composite_readings.py` is a small registry for single values that are really several numbers, applied by `build_lift_observations`: blood pressure `148/92 mmHg, pulse 74` → `Blood Pressure (Systolic)`, `(Diastolic)` and `Heart Rate` observations (the compound text observation is kept for display/NLI); Snellen acuity `20/40` → decimal `0.5` stored on the observation itself; height `5'9"` → `175.3 cm`. Matching is on the base name, so `Visual acuity (right eye)` / `Blood Pressure (sitting)` match and the qualifier is preserved on derived names (each eye/posture stays its own series). Anything unregistered — ratios like `A/G 1.2/1`, dates — is left untouched on purpose; add a handler + dict entry to support a new shape. HbA1c `6.1 % (43 mmol/mol)` is one observation (the first number), not split.
