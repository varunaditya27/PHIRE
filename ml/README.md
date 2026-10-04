# PHIRE `ml/`: RAG, Claim Verification, and the Longitudinal Health Graph

**Owned by Varun (ML & Intelligence).** Retrieval, evidence-attributed claim
verification, and a Neo4j-backed patient fact graph, composed into one QA
pipeline. See the [root README](../README.md) for what PHIRE is as a whole;
this doc covers only `ml/`.

**Status**: Core pipeline implemented and live-tested end-to-end (retrieval
→ generation → claim extraction → NLI verification → confidence scoring →
abstention, grounded in real patient facts from Neo4j). Backend integration
(`backend/` FastAPI wiring with `GPU_LOCK` and `ml_singletons`) is fully
implemented and tested. Unified visual extraction via `datalab-to/lift` 9.7B VLM
replaces the previous multi-pass OCR, table parsing, and prose extraction pipeline.
See [Features & Status](#-features--status) below.

---

## 🎯 What `ml/` Does

- **Hybrid retrieval**: BM25 (lexical) + Chroma (semantic, MedCPT
  embeddings) fused via reciprocal rank fusion, reranked with a MedCPT
  cross-encoder plus authority/recency scoring.
- **Evidence-attributed answers**: a draft LLM answer is decomposed into
  atomic claims, each independently verified via NLI (entailment/
  contradiction) against retrieved evidence — only claims that pass are
  shown, with the exact source (document citation, URL, or graph fact) attached.
- **Longitudinal Health Graph**: structured patient facts (labs,
  medications, conditions) in Neo4j, populated directly from schema-guided
  visual document extraction — read back into chat as current-state facts
  and precomputed trend deltas.
- **Document ingestion**: unified single-pass visual extraction of multi-page
  PDFs and image documents via `datalab-to/lift` 9.7B VLM (with 4-bit NF4
  quantization on CUDA and CPU fallback), Option A declarative clinical sentence
  synthesis for RAG, and fast deterministic mock execution.
- **Reference corpus ingestion**: PubMed abstracts, MedlinePlus summaries,
  USDA FoodData Central nutrition data.

### Not yet implemented
- Fitness/nutrition recommendation models (`ml/recommendations/` is stubs
  only — see [Features & Status](#-features--status))
- Multi-hop graph-RAG retrieval (LightRAG-style entity/relationship
  traversal at query time) — see
  [docs/GRAPH_SCHEMA_ROADMAP.md](../docs/GRAPH_SCHEMA_ROADMAP.md) section 3f

---

## 🏗️ Architecture

```
question
   │
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
ClaimVerifier (BART-large-MNLI) ── verify each claim against:
   │   - reranked reference/document evidence
   │   - current patient facts (Neo4j, via patient_context.py)
   │   - precomputed trend deltas (relabeled DERIVED on match)
   ▼
compute_confidence + ABSTENTION_THRESHOLD
   │
   ▼
ChatResponse (answer built only from verified claims + full audit trail)
```

Every model/library choice is benchmarked, not assumed — see each
subsystem's `experiments/RESULTS.md` (linked below).

---

## 🚀 Quick Start

### Requirements
- Python 3.11 or 3.12, managed via [uv](https://github.com/astral-sh/uv) —
  **not** system Python (see `ml/.venv`)
- A local [Ollama](https://ollama.ai) instance (`OLLAMA_HOST`, default
  `http://localhost:11434`) with `medgemma:4b` pulled
- `datalab-to/lift` VLM model weights (loaded in-process via Hugging Face;
  can be mocked via `PHIRE_MOCK_LIFT=true` for offline/CPU testing)
- A local Neo4j instance for the graph layer (see `ml/.env.example` for the
  exact `podman run` command)
- NVIDIA GPU with 8GB+ VRAM recommended (CPU execution fully supported) — see
  `CLAUDE.md` for this project's hardware assumptions

### Setup

```bash
cd ml
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt

cp .env.example .env   # fill in Neo4j credentials, optional API keys
```

### Run the tests

```bash
source .venv/bin/activate
set -a && source .env && set +a
PHIRE_MOCK_LIFT=true python -m pytest tests/ -q
```

Most tests are pure unit tests (no live services needed). A few require a
live local Neo4j (`test_graph_integration.py`, `test_qa_chain_live_e2e.py`)
— they skip automatically (not error) if Neo4j isn't reachable.

### Ingest something and ask a question

```bash
# Reference corpus (PubMed/MedlinePlus/USDA) — run once to seed data/chroma
python -m ml.rag.ingest.run_ingest

# A patient document (PDF or JPG/PNG)
python -m ml.rag.ingest.ingest_patient_document /path/to/report.pdf
```

```python
from ml.chains.qa_chain import QAChain

chain = QAChain()  # loads models + Neo4j connection — construct once, reuse
response = chain.answer("What was my most recent LDL cholesterol result?")
print(response.answer)
for claim in response.claims:
    print(claim.status, claim.confidence, claim.claim)
```

---

## 📊 Features & Status

**Core**
- [x] Hybrid retrieval (BM25 + Chroma, MedCPT-reranked, patient-document floor)
- [x] Claim extraction + NLI-based verification (SUPPORTED/DERIVED/CONFLICTING/UNCERTAIN/UNSUPPORTED)
- [x] Confidence scoring + abstention
- [x] Longitudinal Health Graph (Neo4j): Observation/Medication/Condition nodes, structured Lift extraction
- [x] Graph read path feeding chat: current facts + precomputed trend deltas
- [x] Patient document ingestion: unified visual extraction via `datalab-to/lift` (PDF + images), Option A RAG chunk synthesis, structured Neo4j graph writes
- [x] Reference corpus ingestion: PubMed, MedlinePlus, USDA FoodData Central
- [x] Backend API integration: FastAPI routers, `ml_singletons`, `GPU_LOCK` serialization, HIPAA audit logging
- [x] Live end-to-end pipeline tests (real Ollama + Neo4j + Chroma, no fakes)

**Not started**
- [ ] Fitness recommendations (`ml/recommendations/fitness/`)
- [ ] Nutrition recommendations (`ml/recommendations/nutrition/`)
- [ ] Multi-hop graph-RAG retrieval (LightRAG-style) — see `docs/GRAPH_SCHEMA_ROADMAP.md` §3f
- [ ] Claim→evidence graph persistence (deferred until chat history is persisted — see `docs/GRAPH_SCHEMA_ROADMAP.md` §3b)

---

## 🛠️ Model & Tool Choices

Every non-trivial choice below was benchmarked against alternatives, not
assumed — see the linked `RESULTS.md` for methodology and numbers.

| Purpose | Choice | Benchmark |
|---|---|---|
| Chat generation | `medgemma:4b` (Ollama) | [`ml/llm/`](llm/) — see `docs/ML_HANDOFF_FOR_ANIKA.md` |
| Visual document extraction | `datalab-to/lift` (9.7B VLM, 4-bit NF4 & CPU fallback) | Schema-guided extraction replacing fragmented olmOCR + table parsing + prose extraction |
| Embeddings | MedCPT dual encoder | [`ml/rag/experiments/RESULTS.md`](rag/experiments/RESULTS.md) |
| Reranking | MedCPT cross-encoder + authority/recency + patient-doc floor | [`ml/rag/reranker_experiments/RESULTS.md`](rag/reranker_experiments/RESULTS.md) |
| Claim verification | BART-large-MNLI (NLI) | [`ml/claims/experiments/RESULTS.md`](claims/experiments/RESULTS.md) |
| Vector store | Chroma (in-process) | `docs/DATASETS_AND_GRAPH_RAG.md` |
| Graph store | Neo4j, direct Cypher (not LightRAG — see above) | `docs/DATASETS_AND_GRAPH_RAG.md` |

---

## 📖 Documentation

- **[docs/ML_HANDOFF_FOR_ANIKA.md](../docs/ML_HANDOFF_FOR_ANIKA.md)** — integration contract for `backend/`: entry points, infrastructure dependencies, known limitations
- **[docs/GRAPH_SCHEMA_ROADMAP.md](../docs/GRAPH_SCHEMA_ROADMAP.md)** — Longitudinal Health Graph: current schema, what's deferred and why, what's outstanding
- **[docs/DATASETS_AND_GRAPH_RAG.md](../docs/DATASETS_AND_GRAPH_RAG.md)** — finalized datasets, model choices, hybrid vector + graph RAG architecture
- **[docs/RESEARCH_LOG.md](../docs/RESEARCH_LOG.md)** — dated findings, bugs found/fixed, and design decisions in a form reusable for paper drafting
- **[docs/PDF_INGESTION_ROADMAP.md](../docs/PDF_INGESTION_ROADMAP.md)** — the scanned-PDF-with-no-text-layer gap: decided design, not yet built

---

## ⚠️ Privacy Boundary

Every network call in `ml/` that talks to Ollama or Neo4j is enforced
local-only at the code level (`ml/local_only.py`), not just by convention —
a misconfigured `OLLAMA_HOST`/`NEO4J_URI` pointing off-box raises, it
doesn't silently proceed. `ml/rag/ingest/{pubmed,medlineplus,usda}.py` are
the one deliberate exception: they fetch public reference literature
(PubMed, MedlinePlus, USDA), never patient data — see each module's
docstring for why that's outside PHIRE's "no cloud APIs for PHI" boundary,
not a violation of it.

---

Last updated: 2026-09-09
