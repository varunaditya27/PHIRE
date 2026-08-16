# Reranker weight tuning: experiment & results

**Question**: `ml/rag/reranker.py` documented a known limitation (found
during patient-document ingestion work): a patient's own record can lose
to generic reference prose in ranking, because MedCPT-Cross-Encoder
saturates relevance near 1.0 for any topically-relevant chunk. The
docstring explicitly declined to re-tune the weights off that one
example, calling for a proper eval set first — this is that eval set.

## Method

**Eval set** (`eval_data.py`): 8 real queries against the **real corpus**
already ingested this session (not synthetic) — 4 "patient-fact" queries
(the correct top result is the patient's own ingested document,
`authority=1.0`) and 4 "general-topic" queries (the correct top result is
public reference material, `authority=0.7-0.9`). Verified live before
authoring each query that both sides of the pair have real matching
content in the corpus.

**Weight configs**: the current weights (0.6/0.25/0.15), two
authority-boosted variants, and a `relevance_only` baseline
(`authority_weight=0`) to isolate authority's actual contribution.
`Reranker`'s weights were made constructor-configurable for this (see
`ml/rag/reranker.py`) rather than editing module constants between runs.

**Metrics** (`metrics.py`): hit@1 and hit@3 — does the top-ranked (or
any of the top 3) result's source match the expected type for that
query's category. One retriever + one reranker instance reused across
all configs (only the weights change; nothing is re-embedded or reloaded).

**Reproduce**: requires the corpus already populated (public reference +
at least one ingested patient document with an LDL/potassium/creatinine
value and a lisinopril mention — see `ml/rag/ingest/run_ingest.py` and
`ml/rag/ingest/ingest_patient_document.py`), then
`ml/.venv/bin/python -m ml.rag.reranker_experiments.run_benchmark`.

## Results

| Config | Patient-fact hit@1 | Patient-fact hit@3 | General-topic hit@1 | General-topic hit@3 |
|---|---|---|---|---|
| **current (0.6/0.25/0.15)** | 0.75 | 0.75 | **1.0** | 1.0 |
| authority_boost_moderate (0.5/0.35/0.15) | 0.75 | 0.75 | 0.75 | 1.0 |
| authority_boost_strong (0.45/0.40/0.15) | 0.75 | 0.75 | 0.75 | 1.0 |
| relevance_only (0.85/0.0/0.15) | **0.25** | 0.75 | 1.0 | 1.0 |

**Authority weighting already earns its keep**: removing it entirely
(`relevance_only`) drops patient-fact hit@1 from 0.75 to 0.25 — three of
four patient-fact queries would fail without it. The documented
limitation is real, but authority isn't doing nothing; it's already
winning 3 of 4 cases.

**Boosting authority further does not fix the remaining failure, and
actively costs general-topic accuracy.** Both boosted configs left
patient-fact hit@1 unchanged at 0.75 (the one failing query — "What is my
LDL cholesterol result?" — fails identically at every authority weight
tested) while dropping general-topic hit@1 from 1.0 to 0.75. **The
current weights are already at a local optimum** on this eval set — this
directly disproves the hypothesis (raised when the limitation was first
documented) that simply raising `AUTHORITY_WEIGHT` would help.

## Root cause, diagnosed precisely (not just theorized)

Inspecting the one consistently-failing query directly: MedCPT-Cross-
Encoder assigns `relevance=1.000` to **seven or eight different
MedlinePlus chunks simultaneously** for "What is my LDL cholesterol
result?" — not one strong competitor edging out the patient's chunk, but
a wide plateau of ties at the ceiling. The patient's own chunk ("LDL
Cholesterol: 162 mg/dL (High)") does rank in the top 5 of the *retrieval*
candidate pool (confirmed: it survives to the reranker), so this is
purely a reranking-stage failure. No realistic authority weight can
outvote that many simultaneous ties — the problem isn't the weight
formula, it's the cross-encoder's calibration on broad-topic queries.
This matches, and now empirically confirms, what `reranker.py`'s
docstring already suspected.

## Limitations

- **N=8 queries**, small by this project's own benchmark standards
  (though appropriately so — this tests a specific hypothesis, not a
  general capability). A larger, more diverse query set might surface
  different failure patterns.
- **Corpus-dependent**: results reflect whatever happens to be ingested
  in this session's local Chroma instance (several test patient
  documents, the public reference corpus from `run_ingest.py`). Re-running
  after further ingestion could shift specific query outcomes, though the
  *mechanism* identified (cross-encoder saturation) is a property of the
  model, not this specific corpus.
- Didn't test weight configs below current authority (e.g. 0.15) or
  above 0.40 — the two tested boosts already showed no patient-fact gain
  with real general-topic cost, so pushing further seemed unlikely to
  reverse that trend, but wasn't verified.

## Decision

**No weight change.** The current weights (`RELEVANCE_WEIGHT=0.6`,
`AUTHORITY_WEIGHT=0.25`, `RECENCY_WEIGHT=0.15`) stay as they are —
they're already better than every alternative tested on this eval set.
Re-tuning them off the original single-example observation, as the
limitation's discovery moment tempted, would have made general-topic
retrieval measurably worse while not fixing the patient-fact case it was
meant to help.

**The real fix is structural, not a weight change** — consistent with
option 3 raised when this limitation was first discussed: guarantee a
patient-document floor (always fold in top-N `source=patient_document`
matches independent of reranking) rather than trusting cross-encoder
scoring to consistently favor them. That's a bigger architectural change,
not implemented here — this experiment's job was to rule out the cheap
fix, not to build the real one.
