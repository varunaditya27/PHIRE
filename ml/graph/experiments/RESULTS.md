# Prose-extraction method & model selection: experiment & results

**Question**: How should `ml/graph/` extract structured facts (medications,
observations) from *free-text* sections of patient documents — progress
notes, radiology reports — where (unlike lab tables) there's no explicit
schema to parse deterministically? See `docs/GRAPH_SCHEMA_ROADMAP.md` for
why this is scoped narrowly (medications + observations only, not the
full clinical-KG architecture surveyed there).

## Method

**Candidates** (`candidates.py`): 2 extraction methods x 3 models = 6
candidates.

- **HandRolled**: direct Ollama call with a full JSON Schema constraint
  (`format` param, grammar-constrained decoding) — the same proven
  pattern as `ml/rag/ingest/ocr.py`.
- **LangExtract** ([google/langextract](https://github.com/google/langextract),
  verified real: Apache-2.0, 38k+ stars, actively maintained): few-shot
  structured extraction with source grounding (maps every extraction to
  its exact character span in the source text). Its Ollama integration
  was verified (by reading its provider source directly, not assumed)
  to only support loose JSON mode, not real schema constraints — a real
  reliability gap, tested here rather than ruled out on that gap alone.
- Models: `medgemma:4b` (already in use elsewhere in PHIRE), `qwen3.5:9b`,
  `qwen3.5:27b-q4_K_M` (quantized; ~17GB, exceeds this machine's 8GB VRAM
  and runs partially on CPU — slow but confirmed not to crash the system).
  `qwen2:7b` was excluded as outdated per explicit direction.

**Eval set** (`eval_data.py`): the 3 real prose/mixed documents from
`ml/rag/ingest/experiments`' OCR benchmark, using **actual olmOCR output**
(including its minor noise, e.g. "Cardiome diastinal" for
"Cardiomediastinal") — not hand-typed ground-truth text, since that's
what extraction actually has to work with in the real pipeline.
`medication_reconciliation` deliberately exercises "continued" vs.
"started" vs. "discontinued" medications in one document, the clinically
meaningful distinction a naive extractor might collapse into one bucket.

**Metrics** (`metrics.py`): fact-level, not text similarity — a
medication's name, dosage, frequency, and status are four independent
things to get right. Name recall is the easy part; status recall is the
one that actually matters for safety (a "discontinued" medication
mis-recorded as "continued" is a real hazard, not just noise).

**Reproduce**: pull all three model tags, then
`ml/.venv/bin/python -m ml.graph.experiments.run_benchmark` from the repo
root (~11 minutes — the 27B candidates alone take ~5-6 minutes each due
to CPU offload). Full per-document extractions in `results.json`.

## Results

| Model | Med Name | Med Dosage | Med Frequency | Med Status | Obs Name | Obs Value |
|---|---|---|---|---|---|---|
| HandRolled + medgemma:4b | 0.933 | 0.933 | 0.933 | 0.933 | 1.0 | 1.0 |
| **HandRolled + qwen3.5:9b** | **1.0** | **1.0** | **1.0** | **1.0** | **1.0** | **1.0** |
| HandRolled + qwen3.5:27b-q4_K_M | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| LangExtract + medgemma:4b | 1.0 | 1.0 | 1.0 | 0.667 | 1.0 | 1.0 |
| LangExtract + qwen3.5:9b | 1.0 | 1.0 | 1.0 | 0.833 | 1.0 | 1.0 |
| LangExtract + qwen3.5:27b-q4_K_M | 1.0 | 1.0 | 1.0 | 0.833 | 1.0 | 1.0 |

**HandRolled beats LangExtract specifically on status accuracy, and
consistently across all three models** (LangExtract: 0.667-0.833; every
HandRolled/qwen3.5 pairing: perfect 1.0). This isn't a one-off — the same
weakness shows up regardless of which model LangExtract is paired with,
pointing at the method (loose JSON mode + few-shot prompting) rather than
any one model's capability. This is consistent with the concern raised
before running this: LangExtract's Ollama path not getting real schema
constraints is a real cost, not just a theoretical one.

**qwen3.5:9b matches qwen3.5:27b-q4_K_M exactly** (perfect on every
metric, both methods) while running **~13x faster** (24.8s vs. 322.8s for
HandRolled) and using a third of the disk/VRAM footprint (6.6GB vs.
17GB). No measured reason to pay the 27B model's resource cost here.

**medgemma:4b's one miss**: it dropped the discontinued Aspirin from
`medication_reconciliation` entirely — the hardest case in the eval set
(negation-adjacent: "Discontinued: Aspirin 81mg daily"). It also emitted
a hallucinated placeholder medication entry
(`{"name": "unspecified", ...}`) on `radiology_report`, which has zero
real medications — invisible to this benchmark's scoring (empty ground
truth scores trivially perfect), but a real false-positive risk in
production a stronger model didn't exhibit. Neither `qwen3.5:9b` nor
`qwen3.5:27b` produced this artifact on the same document.

## Bugs found and fixed while running this (documented, not silently patched)

- **qwen3.5's "thinking" mode silently ate the entire answer.** Ollama's
  `/api/generate` response has a separate `"thinking"` field for
  reasoning models; without `"think": false` in the request, qwen3.5 put
  its (verified, on manual inspection, perfectly correct) answer entirely
  in `"thinking"` and left `"response"` empty — scoring as a total
  failure despite the extraction itself being right. This is a real
  reminder that an empty/failed-looking result isn't automatically a
  capability failure — worth checking the actual response shape before
  concluding a model is bad at a task.
- **LangExtract's default 120s request timeout was too short** for the
  17GB CPU-offloaded model. Fixed via
  `provider_kwargs={"timeout": 600}`.
- **LangExtract's model-id pattern matching doesn't recognize
  "medgemma"** (only matches `^gemma`) — fixed with an explicit
  `factory.ModelConfig(provider="OllamaLanguageModel")` instead of
  relying on auto-detection.
- Made `run_benchmark.py` resilient to a single candidate failing (writes
  results incrementally, catches per-candidate exceptions) after the
  first full run's results were lost when the last candidate crashed.

## Limitations

- **N=3 documents.** Small by this project's own standard (the OCR and
  embedding benchmarks used 8-12 items); prose-extraction ground truth is
  expensive to author well, and this was scoped to validate the
  method/model choice, not to be a definitive accuracy measurement.
  qwen3.5:9b and 27b tying at a perfect score on 3 documents doesn't rule
  out a real gap that a harder/larger eval set would expose — revisit if
  quality problems show up in real use.
- **LangExtract's real capability may be understated here.** Its
  `output_schema` mechanism (real schema constraints) works on other
  providers (e.g. Gemini) — this result specifically reflects its Ollama
  provider's current limitation, not a fundamental ceiling on the
  library. If LangExtract's Ollama support gains real schema constraints
  in a future release, worth re-testing.
- Both methods were given the same two-shot examples/prompt content by
  design, for a fair comparison — neither was tuned further.

## Decision

**Use the HandRolled method with `qwen3.5:9b`** for `ml/graph/`'s
free-text extraction. Best status accuracy (the safety-relevant metric),
ties for best on every other metric, ~13x faster than the 27B alternative
with no measured quality cost, and doesn't exhibit medgemma's
hallucinated-placeholder or dropped-discontinued-medication failures.

Not yet implemented: wiring this into `ml/graph/`'s actual extraction
pipeline (today's `ml/graph/observations.py` only handles table-derived
facts) and adding the `Medication`/`Condition` node types this feeds —
separate next step.
