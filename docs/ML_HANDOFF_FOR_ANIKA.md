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

---

## 1. The two things you actually need to call

Almost everything else in this doc is context for these two entry points.

### 1.1 Answering a chat question — `ml.chains.qa_chain.QAChain`

```python
from ml.chains.qa_chain import QAChain

chain = QAChain()  # loads several models — construct once, reuse, not per-request
response = chain.answer("what was my LDL cholesterol result?")

response.answer   # str — the final answer, built only from verified claims
response.claims   # list[VerifiedClaim] — full audit trail, including dropped claims
```

`VerifiedClaim` fields: `claim: str`, `status: str` (`SUPPORTED` /
`CONFLICTING` / `UNCERTAIN` / `UNSUPPORTED`), `confidence: float` (0-1),
`source_url: str | None` (public reference chunks only), `source_filename:
str | None` (patient documents), `source_span: tuple[int, int] | None`
(exact character offset in the source document — `None` for facts that
aren't extracted verbatim, e.g. table rows; see §4).

All fields are plain Python — `dataclasses.asdict(response)` gives you a
JSON-serializable dict directly for an API response.

**Cost**: `QAChain()`'s constructor loads 4 models onto the GPU (embedding
×2, reranker, claim verifier) — this takes a few seconds and ~2-3GB VRAM.
Build one instance and reuse it across requests in a long-lived process;
don't construct it per-request. `chain.answer()` itself also makes one
Ollama call (chat generation) per question.

### 1.2 Ingesting a patient document — `ml.rag.ingest.ingest_patient_document`

```python
from pathlib import Path
from ml.rag.ingest.ingest_patient_document import build_chunks
from ml.rag.retriever import HybridRetriever

chunks = build_chunks(Path("/path/to/uploaded/file.pdf"))  # or .jpg/.png
HybridRetriever().add_documents(chunks)
```

That indexes the document for retrieval (Chroma + BM25). It does **not**
write structured facts to the graph — that's a separate step, because
prose extraction (an LLM call) is comparatively expensive and you may not
always want it. To do both (what the CLI script does), see
`ml/rag/ingest/ingest_patient_document.py`'s `main()` for the exact
sequence — order matters (§5.3).

Or just shell out to the script directly, which does everything
(chunking, embedding, indexing, graph extraction) in the right order:

```bash
ml/.venv/bin/python -m ml.rag.ingest.ingest_patient_document /path/to/file.pdf
```

Accepts: text-based PDF, or `.jpg`/`.jpeg`/`.png` (routed to OCR). A
**scanned PDF** (image content saved with a `.pdf` extension) is **not**
handled by either path yet — it'll extract as empty text and raise. If
your upload endpoint needs to support that, it needs a real fix in
`ml/rag/ingest/patient_documents.py`, not a backend-side workaround.

---

## 2. Infrastructure this depends on

### 2.1 Ollama (LLM serving — your existing Week 1 responsibility)

Production model requirements — **only these three need to be pulled**,
not everything visible in `ollama list` on this dev machine (most of
those are benchmark candidates, not production dependencies):

| Purpose | Model | Config env var |
|---|---|---|
| Chat generation | `medgemma:4b` | `OLLAMA_MODEL` |
| OCR (scanned/photographed documents) | `hf.co/bartowski/allenai_olmOCR-2-7B-1025-GGUF:Q4_K_M` | `OCR_MODEL` |
| Prose fact extraction (medications/conditions from free text) | `qwen3.5:9b` | `PROSE_EXTRACTION_MODEL` |

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

1. **GPU memory ordering matters.** On an 8GB GPU, running OCR
   extraction, prose extraction, and the embedding model back-to-back in
   one process without releasing VRAM between them will OOM-crash —
   verified live, not theoretical. `ingest_patient_document.py`'s
   `main()` handles this correctly (all Ollama calls finish, with
   `keep_alive: 0`, before the embedding model loads) — if you build
   your own orchestration around these pieces instead of calling that
   script, preserve that ordering.
2. **DERIVED and INFERRED claim statuses are not implemented.** Only
   `SUPPORTED`/`CONFLICTING`/`UNCERTAIN`/`UNSUPPORTED` exist. A claim that
   requires computing something from raw values, or multi-hop reasoning,
   currently just falls into `UNCERTAIN` rather than being specially
   handled — documented gap in `ml/claims/verifier.py`, not a bug.
3. **A scanned PDF (not a photo, an actual PDF with no text layer) isn't
   handled by anything yet** — see §1.2.
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
7. **Prose extraction degrades silently to "no facts found," not an
   exception.** If Ollama is unreachable or returns something
   unparseable during `extract_facts()` (`ml/graph/prose_extraction.py`),
   ingestion doesn't crash — medications/conditions/prose-derived
   observations for that document just come back empty (a warning is
   printed, not raised). Table-derived observations and chunk indexing
   are unaffected either way (they don't depend on this call). If your
   upload endpoint wants to surface "graph extraction partially failed"
   to the user, you'll need to check for an empty facts result yourself —
   `ml/` won't raise for you here by design (a transient LLM hiccup
   shouldn't fail the whole document upload).

---

## 6. Where to look for "why was this model/approach chosen"

Every non-trivial model or library choice in `ml/` was benchmarked, not
assumed — if you need to understand *why* something works the way it
does (or want to challenge a choice), these are the primary sources, not
this doc:

- `ml/rag/experiments/RESULTS.md` — embedding model (MedCPT)
- `ml/claims/experiments/RESULTS.md` — claim verification NLI model (BART-large-MNLI)
- `ml/rag/ingest/experiments/RESULTS.md` — OCR model (olmOCR-v2)
- `ml/graph/experiments/RESULTS.md` — prose extraction method/model (HandRolled + qwen3.5:9b)
- `ml/rag/reranker_experiments/RESULTS.md` — reranker weight tuning + the patient-document floor fix
- `docs/GRAPH_SCHEMA_ROADMAP.md` — what's deliberately deferred in the graph schema, and the trigger condition for each
