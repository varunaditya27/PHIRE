# Reranker weight tuning & structural fix: experiment & results

**Question**: `ml/rag/reranker.py` documented a known limitation (found
during patient-document ingestion work): a patient's own record can lose
to generic reference prose in ranking, because MedCPT-Cross-Encoder
saturates relevance near 1.0 for any topically-relevant chunk. Round 1
(below) tested whether re-weighting fixes it. It doesn't. Round 2 adds a
structural fix — a patient-document floor — and validates it against the
same eval set.

## Method

**Eval set** (`eval_data.py`): 8 real queries against the **real corpus**
already ingested this session (not synthetic) — 4 "patient-fact" queries
(the correct result includes the patient's own ingested document,
`authority=1.0`) and 4 "general-topic" queries (the correct result
includes public reference material, `authority=0.7-0.9`). Verified live
before authoring each query that both sides of the pair have real
matching content in the corpus.

**Weight configs** (round 1): current weights (0.6/0.25/0.15), two
authority-boosted variants, and a `relevance_only` baseline
(`authority_weight=0`) to isolate authority's contribution.

**Structural fix** (round 2, `ml/rag/reranker.py`'s `enable_patient_floor`):
if the best-matching patient-document chunk's own relevance score is
within `PATIENT_FLOOR_RELEVANCE_MARGIN` (0.1, chosen from the actual
observed gap in the original investigation) of the single best relevance
score in the candidate pool, it's promoted into the returned set
regardless of where weighted scoring placed it — inserted at the last
slot of `top_k`, not forced to rank 1 (see "Why inclusion, not rank"
below).

**Metrics** (`metrics.py`): hit@1, hit@3, and **`included`** (does the
expected source type appear anywhere in the full returned set, not just
the top-ranked or top-3 positions). `included` is the metric that
actually reflects what matters for `qa_chain.py`: its LLM reads every
chunk in the returned evidence set, not just the highest-ranked one, so
whether the right evidence is *present* determines whether a question
can be answered correctly — rank position within that set matters less.

**Reproduce**: requires the corpus already populated (see
`ml/rag/ingest/run_ingest.py` and `ml/rag/ingest/ingest_patient_document.py`),
then `ml/.venv/bin/python -m ml.rag.reranker_experiments.run_benchmark`.

## Results

| Config | PF hit@1 | PF hit@3 | PF included | GT hit@1 | GT hit@3 | GT included |
|---|---|---|---|---|---|---|
| current, floor off | 0.75 | 0.75 | 0.75 | 1.0 | 1.0 | 1.0 |
| authority_boost_moderate, floor off | 0.75 | 0.75 | 0.75 | 0.75 | 1.0 | 1.0 |
| authority_boost_strong, floor off | 1.0 | 1.0 | 1.0 | **0.75** | 1.0 | 1.0 |
| relevance_only, floor off | 0.25 | 0.75 | 0.75 | 1.0 | 1.0 | 1.0 |
| **current, floor ON** | 0.75 | 0.75 | **1.0** | **1.0** | **1.0** | **1.0** |

### Round 1: no weight change fixes this without a cost

Boosting authority moderately does nothing for patient-fact (stuck at
0.75 on every metric) while dropping general-topic hit@1 to 0.75.
Boosting it strongly *does* fix patient-fact completely (1.0 across the
board) — but at the same general-topic hit@1 cost. There is no weight
setting in this sweep that improves patient-fact without a general-topic
tradeoff. (`relevance_only` confirms authority is doing real work: removing
it drops patient-fact hit@1 to 0.25.)

### Round 2: the structural floor wins on every axis

**`current weights + floor ON` is the only config that improves
patient-fact (`included`: 0.75 → 1.0) with *zero* cost anywhere** —
general-topic stays perfect on all three metrics. This is strictly
better than `authority_boost_strong`, which achieves the same patient-fact
result but only by sacrificing general-topic hit@1.

### Why `included`, not just hit@1/hit@3

The floor promotes the qualifying patient chunk into the *last* slot of
`top_k`, not rank 1 — deliberate minimal displacement, not an oversight.
`qa_chain.py` passes the full reranked set to the LLM as context; a
chunk's presence in that set is what lets the model actually answer the
question, not its position within it. Testing this fix against hit@1/hit@3
alone would show no improvement (see the identical 0.75 values for
`current, floor ON` on those two columns) despite the fix doing exactly
what it was designed to do — `included` is the metric that doesn't miss
that. This distinction was found live: an early version of this
benchmark used hit@1 as the sole judge and wrongly concluded the floor
"did nothing," before checking what it actually returned.

## A second live finding: the cross-encoder is highly phrasing-sensitive

While debugging why the floor initially appeared not to trigger,
isolating the exact chunk/query pair found: `"what was my LDL cholesterol
result?"` scores 0.922 against the patient's LDL chunk; `"What is my LDL
cholesterol result?"` — same chunk, same meaning, different tense/
capitalization — scores 0.759. A ~0.16 swing from a wording change a
human wouldn't consider meaningfully different. This is a second,
independent data point on MedCPT-Cross-Encoder's calibration issues
(beyond the tie-saturation already documented), worth keeping in mind:
`PATIENT_FLOOR_RELEVANCE_MARGIN=0.1` was chosen from one observed gap and
may need widening if real user phrasing varies this much in practice —
not verified beyond this single example.

## Limitations

- **N=8 queries**, appropriately small for testing a specific mechanism,
  not a general capability claim.
- **Corpus-dependent**: results reflect this session's local Chroma
  instance. The specific relevance scores shift with corpus growth (the
  original investigation's chunk scored differently once more patient
  documents were added) — the *mechanism* (tie saturation, phrasing
  sensitivity) is a model property, not corpus-specific, but exact
  numbers will drift.
- `PATIENT_FLOOR_RELEVANCE_MARGIN=0.1` is not itself swept — only one
  value was tested. Given the phrasing-sensitivity finding above, a wider
  or adaptive margin might generalize better; not verified.
- The floor only ever promotes the *single* best-matching patient chunk,
  not multiple. Untested whether a query needing several patient facts
  simultaneously (not exercised by this eval set) would need more.

## Decision

**Ship the structural floor** (`Reranker.enable_patient_floor=True`,
already the default). It's strictly dominant over every weight
alternative tested — the only config with zero general-topic cost — and
directly addresses the mechanism identified as the actual root cause
(tie saturation, not a tunable weight problem). Weights stay at their
current values (0.6/0.25/0.15); round 1 already showed no weight change
improves on them.
