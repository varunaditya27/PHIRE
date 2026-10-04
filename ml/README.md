# PHIRE `ml/`: RAG, Claim Verification, and the Longitudinal Health Graph

**Owned by Varun (ML & Intelligence).** Retrieval, evidence-attributed claim
verification, and a Neo4j-backed patient fact graph, composed into one QA
pipeline. See the [root README](../README.md) for what PHIRE is as a whole;
this doc covers only `ml/`.

**Status**: Core pipeline implemented and live-tested end to end, on a GPU
and on a CPU-only configuration: document extraction → graph and search
index → retrieval (BM25 + Chroma + question-focused graph retrieval) →
generation → claim extraction → NLI verification → confidence scoring →
abstention. `backend/` and `frontend/` are wired to it and run in Docker
(see [docs/BACKEND_HANDOFF.md](../docs/BACKEND_HANDOFF.md)). See
[Features & Status](#-features--status) below.

---

## 🎯 What `ml/` Does

- **Hybrid retrieval**: BM25 (lexical) + Chroma (semantic, MedCPT
  embeddings) fused via reciprocal rank fusion, reranked with a MedCPT
  cross-encoder plus authority/recency scoring.
- **Graph retrieval** (`ml/graph/graph_retrieval.py`): links the question to
  metrics, medications and conditions in the patient graph, follows one hop
  between them (a statin → the lipid panel, via the curated table in
  `relations.py`), and returns full histories with an overall-change summary
  and any conflicting records (`conflicts.py`). Returns nothing when the
  question links to nothing, and chat falls back to the full fact dump.
- **Evidence-attributed answers**: a draft LLM answer is decomposed into
  atomic claims, each independently verified via NLI (entailment/
  contradiction) against retrieved evidence — only claims that pass are
  shown, with every source attached (document files — all of them for a
  trend — URL, or graph fact).
- **Longitudinal Health Graph**: structured patient facts (labs,
  medications, conditions) in Neo4j, populated from schema-guided document
  extraction — read back into chat as current-state facts, trend deltas and
  question-focused history. Composite readings are split into numeric
  observations (`composite_readings.py`: blood pressure + pulse, Snellen
  acuity, feet-inches height).
- **Document extraction** (one interface, two implementations, chosen by
  `PHIRE_EXTRACTOR=auto|lift|ollama`):
  - `LiftExtractor` — `datalab-to/lift` 9.7B VLM, single pass over PDFs and
    images, **4-bit NF4 applied by the extractor itself** (lift's own loader
    ignores quantization kwargs), ~6.5GiB peak, weights freed after each
    document. GPU machines.
  - `OllamaVisionExtractor` — page images plus the PDF's text layer sent to a
    local multimodal Ollama model (`medgemma:4b`) with schema-constrained
    output. CPU-only machines (see [docs/CPU_SETUP.md](../docs/CPU_SETUP.md)).
  Both feed the same validation, Option A declarative clinical-sentence chunk
  synthesis, and graph writes.
- **Reference corpus ingestion**: PubMed abstracts, MedlinePlus summaries and
  USDA FoodData Central nutrition data, rendered as natural-language
  sentences (USDA includes FDA "high / good source" statements) so NLI can
  verify conversational claims against them.

### Not yet implemented
- Fitness/nutrition recommendation models (`ml/recommendations/` is stubs
  only)
- A single traversal from the patient graph into a guideline passage in
  Chroma (the two legs are combined in the prompt, not walked as one path),
  claim→evidence graph persistence, ontology alignment — deferred with
  trigger conditions in
  [docs/GRAPH_SCHEMA_ROADMAP.md](../docs/GRAPH_SCHEMA_ROADMAP.md)

---

## 🏗️ Architecture

```
question
   │
   ├─► graph retrieval (Neo4j): entity linking → one-hop expansion →
   │   histories / change summaries / conflicting records      (or None)
   ▼
HybridRetriever (BM25 + Chroma, RRF fusion)
   │
   ▼
Reranker (MedCPT cross-encoder + authority/recency + patient-doc floor)
   │
   ▼
OllamaClient.generate (medgemma:4b) ── draft answer
   │
   ▼
ClaimExtractor (medgemma:4b) ── atomic claims
   │
   ▼
ClaimVerifier (BART-large-MNLI, batched, fp16 on CUDA) ── verify each claim against:
   │   - reranked reference/document evidence
   │   - current patient facts + the linked metrics' history (Neo4j)
   │   - precomputed trend deltas and graph-derived sentences (relabeled DERIVED on match)
   ▼
compute_confidence + ABSTENTION_THRESHOLD
   │
   ▼
ChatResponse (answer built only from verified claims, full audit trail,
              every claim's source files, and the evidence it was drafted from)
```

Every model/library choice is benchmarked, not assumed — see each
subsystem's `experiments/RESULTS.md` (linked below).

---

## 🚀 Quick Start

### Requirements
- Python **3.12** (lift-pdf requires ≥ 3.12), managed via
  [uv](https://github.com/astral-sh/uv) — **not** system Python (see `ml/.venv`)
- A local [Ollama](https://ollama.ai) instance (`OLLAMA_HOST`, default
  `http://localhost:11434`) with `medgemma:4b` pulled
- A local Neo4j instance for the graph layer (see `ml/.env.example` for the
  exact `podman run` command)
- **GPU machine**: an NVIDIA GPU with 8GB VRAM (see `CLAUDE.md` for this
  project's hardware assumptions). **CPU-only machine**: 16GB RAM recommended
  — see [docs/CPU_SETUP.md](../docs/CPU_SETUP.md)

### Setup

```bash
cd ml
uv venv --python 3.12
source .venv/bin/activate

# GPU machine (CUDA): base + lift
uv pip install -r requirements.txt -r requirements-lift.txt
# CPU-only machine: CPU PyTorch + base (no lift)
#   uv pip install torch --index-url https://download.pytorch.org/whl/cpu
#   uv pip install -r requirements.txt
# Optional, only to re-run benchmarks: -r requirements-experiments.txt

cp .env.example .env   # fill in Neo4j credentials, optional API keys
```

### Run the tests

```bash
source .venv/bin/activate
set -a && source .env && set +a        # or export NEO4J_URI / NEO4J_PASSWORD
python -m pytest tests/ -q
```

`ml/tests/conftest.py` runs lift in mock mode by default, so no test loads
the 9.7B model. Most tests are pure unit tests; the graph-integration tests
need a live Neo4j and **skip** (not error) when none is reachable — point
`NEO4J_URI`/`NEO4J_PASSWORD` at PHIRE's own Neo4j, never at another project's.
`test_retriever_integration.py` and `test_qa_chain_live_e2e.py` load real
models / need live infrastructure: stop the backend first (GPU memory) or
deselect them. Current state: **312 tests passing** with Neo4j reachable (7 live/GPU-bound tests deselected).

### Ingest something and ask a question

```bash
# Reference corpus (PubMed/MedlinePlus/USDA) — run once to seed data/chroma
python -m ml.rag.ingest.run_ingest

# Upgrade an already-seeded corpus to the current text format, offline (idempotent; stop the backend first)
python -m ml.rag.ingest.reformat_corpus --dry-run

# A patient document (PDF or JPG/PNG)
python -m ml.rag.ingest.ingest_patient_document /path/to/report.pdf
```

```python
from ml.chains.qa_chain import QAChain

chain = QAChain()  # loads models + Neo4j connection — construct once, reuse
response = chain.answer("How is my statin working?")
print(response.answer)
for claim in response.claims:
    print(claim.status, claim.confidence, claim.source_filenames, claim.claim)
```

---

## 📊 Features & Status

**Core**
- [x] Hybrid retrieval (BM25 + Chroma, MedCPT-reranked, patient-document floor)
- [x] Graph retrieval: entity linking, one-hop expansion, full-history/change summaries, conflicting-record detection
- [x] Claim extraction + NLI-based verification (SUPPORTED/DERIVED/CONFLICTING/UNCERTAIN/UNSUPPORTED); an entailing chunk beats contradictions from unrelated chunks; batched, fp16 on CUDA (identical accuracy on the 129 labeled pairs)
- [x] Confidence scoring + abstention
- [x] Every claim cites all its source documents (`source_filenames`); chat `citations` carries the evidence the answer was drafted from
- [x] Longitudinal Health Graph (Neo4j): Observation/Medication/Condition nodes, structured extraction, composite-reading splitting
- [x] Patient document ingestion with lift (GPU) or the Ollama vision model (CPU), Option A RAG chunk synthesis, structured graph writes; a missing clinical date is returned to the caller (`extract_document_date` → `None`) instead of silently using today
- [x] Reference corpus ingestion (PubMed, MedlinePlus, USDA FoodData Central) with natural-language evidence text, plus the offline `reformat_corpus` upgrade tool
- [x] Backend integration: FastAPI routers, `ml_singletons`, LIFT/CHAT GPU modes (`gpu_modes.py`), SSE progress (`QAChain.answer(on_progress=...)`), HIPAA audit logging
- [x] Live end-to-end verification on real models (GPU run and CPU-container run), not only mocks

**Not started**
- [ ] Fitness recommendations (`ml/recommendations/fitness/`)
- [ ] Nutrition recommendations (`ml/recommendations/nutrition/`)
- [ ] Claim→evidence graph persistence (deferred until it is needed — see `docs/GRAPH_SCHEMA_ROADMAP.md` §3b)

---

## 🛠️ Model & Tool Choices

Every non-trivial choice below was benchmarked against alternatives, not
assumed — see the linked `RESULTS.md` for methodology and numbers.

| Purpose | Choice | Benchmark |
|---|---|---|
| Chat generation | `medgemma:4b` (Ollama) | [`ml/llm/`](llm/) — see `docs/ML_HANDOFF_FOR_ANIKA.md` |
| Visual document extraction | GPU: `datalab-to/lift` (9.7B VLM, 4-bit NF4 applied in `LiftExtractor`). CPU: `medgemma:4b` vision via Ollama with schema-constrained output | Schema-guided extraction replacing the retired olmOCR + table parsing + prose extraction; CPU path measured in `docs/CPU_SETUP.md` |
| Embeddings | MedCPT dual encoder | [`ml/rag/experiments/RESULTS.md`](rag/experiments/RESULTS.md) |
| Reranking | MedCPT cross-encoder + authority/recency + patient-doc floor | [`ml/rag/reranker_experiments/RESULTS.md`](rag/reranker_experiments/RESULTS.md) |
| Claim verification | BART-large-MNLI (NLI) | [`ml/claims/experiments/RESULTS.md`](claims/experiments/RESULTS.md) |
| Vector store | Chroma (in-process) | `docs/DATASETS_AND_GRAPH_RAG.md` |
| Graph store | Neo4j, direct Cypher (not LightRAG — see `docs/GRAPH_SCHEMA_ROADMAP.md` §3f) | `docs/DATASETS_AND_GRAPH_RAG.md` |

---

## 📖 Documentation

- **[docs/ML_HANDOFF_FOR_ANIKA.md](../docs/ML_HANDOFF_FOR_ANIKA.md)** — integration contract for `backend/`: entry points, infrastructure dependencies, known limitations
- **[docs/GRAPH_SCHEMA_ROADMAP.md](../docs/GRAPH_SCHEMA_ROADMAP.md)** — Longitudinal Health Graph: current schema, graph retrieval, what's deferred and why
- **[docs/DATASETS_AND_GRAPH_RAG.md](../docs/DATASETS_AND_GRAPH_RAG.md)** — finalized datasets, model choices, hybrid vector + graph RAG architecture
- **[docs/CPU_SETUP.md](../docs/CPU_SETUP.md)** — the CPU-only configuration: setup, measured timings, limits
- **[docs/RESEARCH_LOG.md](../docs/RESEARCH_LOG.md)** — dated findings, bugs found/fixed, and design decisions in a form reusable for paper drafting
- **[docs/PDF_INGESTION_ROADMAP.md](../docs/PDF_INGESTION_ROADMAP.md)** — historical: the superseded scanned-PDF router design

---

## ⚠️ Privacy Boundary

Every network call in `ml/` that talks to Ollama or Neo4j is enforced
local-only at the code level (`ml/local_only.py`), not just by convention —
a misconfigured `OLLAMA_HOST`/`NEO4J_URI` pointing off-box raises, it
doesn't silently proceed. That includes the Ollama vision extractor.
`ml/rag/ingest/{pubmed,medlineplus,usda}.py` are the one deliberate
exception: they fetch public reference literature (PubMed, MedlinePlus,
USDA), never patient data — see each module's docstring for why that's
outside PHIRE's "no cloud APIs for PHI" boundary, not a violation of it.

---

Last updated: 2026-10-05
