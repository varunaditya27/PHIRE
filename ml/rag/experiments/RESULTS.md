# Embedding model selection: experiment & results

**Question**: Which fully-local embedding model should PHIRE use for
`ml/rag/embeddings.py`? Two rounds of this experiment have been run; this
document reflects the second, much larger round. The first round's
conclusion (favoring BGE-base-en-v1.5 on a 12-query/24-passage set) is
**superseded** by this round's larger, more statistically meaningful
result — see "What changed" below.

## Method

**Candidates** (`candidates.py`): 7 models, all runnable fully local
(one-time Hugging Face download, zero network calls at inference), spanning
medical-specialized and general-purpose, base and large sizes:

| Model | Type | Params |
|---|---|---|
| `NeuML/pubmedbert-base-embeddings` | Medical, PubMed-abstract-tuned | ~110M |
| `FremyCompany/BioLORD-2023` | Medical, clinical-sentence-tuned | ~110M |
| `ncbi/MedCPT` (dual encoder) | Medical, retrieval-specific | ~2x110M |
| `BAAI/bge-base-en-v1.5` | General, SOTA contrastive | ~110M |
| `BAAI/bge-large-en-v1.5` | General, SOTA contrastive | ~335M |
| `intfloat/e5-large-v2` | General, SOTA contrastive | ~335M |
| `mixedbread-ai/mxbai-embed-large-v1` | General, SOTA contrastive | ~335M |

All ran on this machine's GPU (RTX 5050 Laptop, 8GB VRAM — see CLAUDE.md's
Hardware section); candidates are built, evaluated, and discarded one at a
time so 7 models never share VRAM simultaneously.

**Eval set** (`eval_data/`, split across `labs.py`, `medications.py`,
`vitals_screening.py`, `conditions.py`): **215 passages across 43 clinical
topics** (15 labs, 10 medications, 9 vitals/screening, 9 conditions/
history), 5 passages per topic, written in clinical-note/lab-report style
(values, units, dates). **129 queries**, 3 per topic — literal clinical
phrasing, lay-language paraphrase, and abbreviation-heavy phrasing. A
query's relevant set is every passage under its topic (label = topic
membership, assigned programmatically, not a subjective per-pair
judgment). This is roughly a **9x scale-up** in passages and **10.75x** in
queries over the first round.

**Retrieval**: pure cosine similarity, no BM25/fusion/reranker — isolates
embedding quality specifically.

**Metrics** (`metrics.py`): Recall@3, Recall@5, Recall@10, Mean Reciprocal
Rank — standard IR metrics, averaged over all 129 queries.

**Reproduce**: `ml/.venv/bin/python -m ml.rag.experiments.run_benchmark`
from the repo root (~5-6 minutes on this GPU, dominated by downloading the
three ~335M-param models on first run). Full per-query rankings are in
`results.json` alongside this file for audit.

## Results

| Model | Recall@3 | Recall@5 | Recall@10 | MRR |
|---|---|---|---|---|
| PubMedBERT (medical) | 0.4791 | 0.6651 | 0.8357 | **0.9475** |
| BioLORD-2023 (medical) | 0.4791 | 0.7302 | 0.8775 | 0.8917 |
| **MedCPT (medical)** | **0.4977** | **0.7721** | **0.9194** | 0.9271 |
| BGE-base-en-v1.5 (general) | 0.4961 | 0.7364 | 0.8760 | 0.9378 |
| BGE-large-en-v1.5 (general) | 0.4760 | 0.6667 | 0.8357 | 0.9196 |
| E5-large-v2 (general) | 0.4667 | 0.6527 | 0.8047 | 0.8878 |
| MXBai-embed-large-v1 (general) | 0.4806 | 0.7302 | 0.8899 | 0.8985 |

**MedCPT wins on Recall@5, Recall@10, and ties-best on Recall@3** — the
clearest, most consistent leader in this round. PubMedBERT retains the
single highest MRR, but its recall is the weakest of all seven, meaning it
finds the *first* relevant passage reliably but misses more of the rest of
the relevant set than MedCPT does. Notably, the larger general-purpose
models (BGE-large, E5-large-v2) did **not** outperform their smaller/
medical-specialized counterparts here — bigger was not simply better.

## What changed from round 1

Round 1 (12 queries, 24 passages, 4 candidates) found BGE-base-en-v1.5
matched-or-led everything and recommended it as the production default.
That default was applied. This round, at ~10x the eval-set size and with
3 additional candidates, tells a different story: **MedCPT leads**, and
BGE-base is now solidly mid-pack rather than best. This is exactly the
outcome a small pilot experiment is supposed to catch before it hardens
into a wrong default — round 1's sample size was too small to trust as a
final answer, which is why round 2 was run at this scale.

## Limitations (read before trusting this too far)

- **Topic labels are mutually exclusive but not always clinically
  independent.** Spot-checking MedCPT's results surfaced two cases where
  this measurably hurts recall: (1) "What is the patient's kidney function
  status?" is labeled relevant only to the `creatinine_gfr` topic, but
  MedCPT's top results were `chronic_kidney_disease` passages — a
  clinically reasonable answer, scored as a miss by this dataset's binary
  topic labels. (2) Thyroid-related queries for `tsh`, `free_t4`, and
  `levothyroxine` topics show similar cross-topic bleed. This penalizes
  **all seven candidates equally** (same eval set, same labels), so
  relative model ranking should still be valid, but it means every
  absolute recall number here is a lower bound, not a ceiling.
- **N=129 queries, N=215 passages.** Much larger than round 1, but still
  synthetic, not PHIRE's real ingested documents or ArchEHR-QA (not yet
  downloaded — Shashwati's task per `docs/AGGRESSIVE_ROADMAP.md`). Re-run
  against ArchEHR-QA once available.
- **No BM25/fusion/reranker** — isolates embedding quality only.
  `retriever.py`'s full hybrid pipeline may narrow or widen these gaps.
- Single deterministic run (embedding inference is deterministic at these
  settings — repeating it would reproduce identical numbers, not add
  signal).

## Decision

**Switched `ml/rag/embeddings.py`'s default to MedCPT**, given it leads on
3 of 4 metrics at 10x the scale of the study that had picked BGE-base.
This required restructuring `EmbeddingModel` from a single
Sentence-Transformers model to MedCPT's true dual-encoder interface
(separate query/article models, manual CLS pooling) — a bigger change than
swapping a model string, confirmed and implemented after review. The
external `embed_documents`/`embed_query` interface `ml/rag/retriever.py`
depends on is unchanged, so no other code needed to change.

Still worth re-confirming once ArchEHR-QA (Shashwati's task, not yet
downloaded) is available — see Limitations above.
