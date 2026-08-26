# NLI model selection: experiment & results

**Question**: Which fully-local NLI model should drive `ml/claims/verifier.py`'s
claim-verification entailment scoring? MedRAGChecker (the paper PHIRE's docs
cite for this) is not a pip-installable library —
`docs/OPEN_SOURCE_TOOLS.md` itself lists "MedRAGChecker pseudocode -> Python"
as a TODO — so this experiment picks the actual model, applying the same
methodology used for the embedding-model benchmark
(`ml/rag/experiments/RESULTS.md`).

## Method

**Candidates** (`candidates.py`): 6 models, all runnable fully local
(one-time Hugging Face download, zero network calls at inference), spanning
MedNLI-finetuned (medical) and standard MNLI (general-purpose):

| Model | Type | Params |
|---|---|---|
| `pritamdeka/PubMedBERT-MNLI-MedNLI` | Medical, MedNLI-finetuned | ~110M |
| `cnut1648/biolinkbert-mednli` | Medical, MedNLI-finetuned | ~110M |
| `cross-encoder/nli-deberta-v3-base` | General, standard MNLI | ~184M |
| `facebook/bart-large-mnli` | General, standard MNLI | ~407M |
| `microsoft/deberta-large-mnli` | General, standard MNLI | ~400M |
| `FacebookAI/roberta-large-mnli` | General, standard MNLI | ~355M |

Each candidate's label ordering was read from its own `config.json`
(`id2label`) rather than assumed — verified individually before being added
here, since NLI checkpoints don't share a standard label index order (e.g.
`microsoft/deberta-large-mnli` orders CONTRADICTION/NEUTRAL/ENTAILMENT while
`facebook/bart-large-mnli` orders contradiction/neutral/entailment).

All ran on this machine's GPU (RTX 5050 Laptop, 8GB VRAM — see CLAUDE.md's
Hardware section); candidates are built, evaluated, and discarded one at a
time so all six never share VRAM simultaneously.

**Eval set** (`eval_data.py`): **129 premise/hypothesis pairs** across the
same **43 clinical topics** validated in the embedding-model benchmark
(labs, medications, vitals/screening, conditions). Premises are reused
verbatim from `ml/rag/experiments/eval_data` (each topic's first passage,
already-vetted clinical-note-style text) — not rewritten here. For each
topic, three hypotheses were hand-authored: one **entailed** by the premise,
one that **contradicts** it, and one **neutral** (plausible in context but
not addressed by the premise). 43 topics x 3 labels = 129 pairs, perfectly
label-balanced.

**Metrics** (`metrics.py`): overall accuracy plus per-class precision/
recall/F1 for entailment/neutral/contradiction — a model that's accurate
overall but weak specifically at catching contradictions would be dangerous
for PHIRE's "never surface a conflicting claim as fact" requirement, so
per-class F1 (especially contradiction) matters as much as the aggregate
number.

**Reproduce**: `ml/.venv/bin/python -m ml.claims.experiments.run_benchmark`
from the repo root (~7 minutes on this GPU). Full per-pair predictions are
in `results.json` alongside this file for audit.

## Results

| Model | Accuracy | Entailment F1 | Neutral F1 | Contradiction F1 |
|---|---|---|---|---|
| PubMedBERT-MedNLI (medical) | 0.9147 | 0.9149 | 0.8974 | 0.9302 |
| BioLinkBERT-MedNLI (medical) | 0.9302 | 0.9149 | 0.9250 | 0.9524 |
| DeBERTa-v3-base-NLI (general, 184M) | 0.8605 | 0.8378 | 0.8085 | 0.9333 |
| **BART-large-MNLI (general, 407M)** | **0.9690** | **0.9767** | **0.9663** | **0.9639** |
| DeBERTa-large-MNLI (general, 400M) | 0.9457 | 0.9762 | 0.9286 | 0.9333 |
| RoBERTa-large-MNLI (general, 355M) | 0.9457 | 0.9767 | 0.9268 | 0.9333 |

**BART-large-MNLI wins on all four metrics** — the clearest, most consistent
leader, and notably a *general-purpose* model beating both MedNLI-finetuned
medical models. This runs counter to the pattern elsewhere in `ml/rag/`
(MedCPT beat general embedding models), so it was spot-checked rather than
taken at face value — see below.

### Why the general model wins here (spot-check)

Comparing PubMedBERT-MedNLI's errors against BART-large-MNLI's correct
predictions on the same pairs (11 cases) shows a consistent pattern: the
medical model over-predicts entailment/contradiction on pairs that are
actually **neutral** — e.g. it labels "The patient's next physical is
scheduled for one year from now" as *entailed* by an immunization-status
premise it has no real bearing on, and "The patient was referred to a
nephrologist for ongoing care" as *entailed* by a CKD-diagnosis premise that
doesn't actually mention a referral. MedNLI's training data is real clinical
progress notes with a particular style; the general MNLI models' much larger
and more diverse training data (MNLI + the datasets each checkpoint
additionally trained on) appears to generalize better to this eval set's
plain declarative-sentence style than the medical fine-tune does. This is a
genuine, spot-checked finding, not an artifact — see Limitations for what it
doesn't prove.

## Limitations (read before trusting this too far)

- **This measures pure 3-way NLI accuracy (entailment/neutral/
  contradiction), not PHIRE's 6-way claim status taxonomy** (SUPPORTED,
  DERIVED, INFERRED, UNCERTAIN, CONFLICTING, UNSUPPORTED). `verifier.py`
  maps the winning model's output onto that taxonomy using retrieval
  presence + entailment/contradiction probability thresholds — DERIVED
  (claim requires computing something from raw values) and INFERRED (claim
  requires multi-hop reasoning beyond direct restatement) aren't
  distinguishable from the NLI signal alone with the current single-model
  approach, and are called out as an explicit v1 limitation in
  `verifier.py` rather than approximated.
- **N=129 pairs, 43 topics, one premise per topic.** Larger than a
  spot-check, but each topic contributes only 3 pairs; a topic-specific
  quirk in the premise or hand-authored hypotheses could shift that topic's
  contribution to the aggregate more than a truly independent sample would.
- **Premises are single sentences from a synthetic clinical-note-style eval
  set** (same one used for the embedding benchmark), not real ingested
  reference passages (PubMed abstracts, MedlinePlus summaries) or real
  patient records. The "general beats medical" result may not hold against
  messier real-world premise text — worth re-checking once claim
  verification runs against actual `ml/rag/ingest`-sourced evidence.
- **Hypotheses were authored by the same person building the benchmark**,
  same caveat as the embedding benchmark's eval set: label = topic-grounded
  construction, not independent expert judgment.
- Single deterministic run (inference is deterministic at these settings).
- **Live spot-check against real ingested evidence surfaced a threshold
  miscalibration for structured (non-prose) premises.** "Salmon is a good
  source of protein" against the real USDA-sourced premise "Fish, salmon,
  pink, cooked, dry heat — per 100g: Energy 153 kcal, Protein 24.6 g..."
  scored only 0.301 entailment (below the 0.7 threshold, so it lands as
  UNCERTAIN despite being clearly true and directly supported) — the model
  was benchmarked exclusively against natural-language clinical-note
  prose, and terse "key: value" nutrition text isn't a premise style it
  was calibrated against. `verifier.py` should not be trusted at face
  value for nutrition claims against USDA evidence until this is either
  fixed (rephrasing USDA chunks as prose at ingestion time, or a
  source-aware threshold) or re-benchmarked with structured premises
  included in the eval set.

## Decision

**`ml/claims/verifier.py` uses `facebook/bart-large-mnli`** for entailment
scoring, given it leads on all four metrics with meaningful margins over
both medical-specialized candidates. This is a deliberate departure from
this project's general pattern of preferring medical-specialized models
(MedCPT for embeddings/reranking) — the data doesn't support that pattern
holding here, and picking the medical model anyway despite it losing this
comparison would be exactly the kind of unexamined assumption these
benchmarks exist to catch.

Worth re-running once claim verification operates against real ingested
evidence (see Limitations) rather than this benchmark's synthetic premises.
