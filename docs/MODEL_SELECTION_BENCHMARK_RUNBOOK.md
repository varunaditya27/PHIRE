# PHIRE Pipeline Model Selection Benchmark Runbook

## Purpose

This runbook explains how to use `ml/graph/experiments/run_pipeline_model_selection.py` to make a reproducible decision about:

1. which structured-extraction model PHIRE should use;
2. whether the existing `qwen3.5:9b` extractor is unnecessarily large;
3. whether `MedGemma 1.5 4B`, `NuExtract3 4B`, or another candidate can replace it;
4. whether `olmOCR` is actually necessary, should be a fallback only, or can be removed for a document class;
5. whether a lighter OCR path such as native PDF text or RapidOCR preserves the clinically important information.

The benchmark evaluates the **pipeline combination**, not just isolated model scores.

---

## Required experimental rule

Every extraction candidate must be evaluated with Ollama's structured-output JSON Schema through the `format` request field. Prompting the model to "return JSON" without schema-constrained decoding is not an equivalent experiment and must not be used for the primary comparison.

The benchmark also uses deterministic scoring for clinical fields. An LLM judge is not allowed to override a wrong medication dose, laboratory number, unit, date, or medication status.

---

## Candidate set

At minimum test:

- current production baseline: `qwen3.5:9b`;
- smaller same-family candidate: `qwen3.5:4b`;
- current conversational model where available: `medgemma:4b`;
- current/new medical 4B candidate where installed;
- `NuExtract3` 4B where installed;
- any additional candidate justified by a separate experiment.

The script discovers installed Ollama tags and skips unavailable candidates rather than pretending a model was evaluated.

Do not change the production configuration merely because a candidate has a lower parameter count.

---

## OCR candidates

The benchmark treats OCR as a **pipeline decision**.

Evaluate, where applicable:

1. native PDF extraction with `pypdf`;
2. RapidOCR;
3. `olmOCR` through Ollama vision;
4. a native-first fallback policy.

The correct outcome may be:

- no OCR for native digital PDFs;
- lightweight OCR for scans/photos;
- `olmOCR` only for hard cases;
- or no dedicated OCR if a lighter path meets the clinical accuracy gates.

`olmOCR` must therefore earn its place with measurable incremental value.

---

## Gold data requirements

Do not run the final selection on the three-document prose experiment alone.

The final manifest should contain a patient-level held-out test set covering:

- Indian laboratory reports;
- Indian prescriptions, including handwriting where possible;
- OP consultation notes;
- discharge summaries;
- radiology/pathology prose;
- wellness/vitals records;
- mixed historical records;
- digital PDFs;
- scanned PDFs;
- photographed pages;
- tables;
- two-column layouts;
- noisy/rotated/compressed documents;
- medication start/stop/continue/change cases;
- negation and uncertainty;
- temporality;
- contradictory reports;
- missing facts;
- unit variants and common Indian abbreviations.

The full benchmark design is specified in `docs/PHIRE_BENCHMARK_SPEC.md`.

---

## Gold extraction schema

Each case should provide gold arrays for:

- observations;
- medications;
- conditions.

The current script scores these fields:

### Observation

- name;
- value;
- unit;
- date;
- reference range;
- interpretation.

### Medication

- name;
- dose;
- frequency;
- route;
- duration;
- status;
- date.

### Condition

- name;
- status;
- certainty;
- temporality;
- date.

The benchmark treats observation value/unit/date and medication name/dose/frequency/status/date as clinically critical fields.

Expand the schema before the final benchmark if PHIRE's production graph schema adds additional attributes.

---

## Run sequence

### 1. Verify the local Ollama service

```bash
curl http://localhost:11434/api/tags
```

Confirm every intended candidate is actually installed.

### 2. Prepare the manifest

Copy:

`ml/graph/experiments/eval_data/pipeline_manifest.example.json`

to a local evaluation manifest and replace the placeholder paths/gold labels.

Do not commit PHI or restricted datasets.

### 3. Run the extraction comparison

```bash
python -m ml.graph.experiments.run_pipeline_model_selection \
  --manifest /path/to/pipeline_manifest.json \
  --models medgemma:4b,qwen3.5:4b,qwen3.5:9b \
  --out ml/graph/experiments/pipeline_selection_results
```

Add `NuExtract3` or other installed tags explicitly when available.

### 4. Run OCR-only analysis when the document set contains image/PDF cases

The default command evaluates native, RapidOCR, and optional `olmOCR` acquisition paths. Set `--olmocr-model` to the exact installed vision model tag.

### 5. Inspect all three outputs

- `results.json`: raw per-case outputs and metrics;
- `summary.json`: aggregate metrics and the deterministic gate decision;
- `decision.md`: generated human-readable recommendation.

Never discard the raw results.

---

## Hard selection gates

A candidate is eligible only if all hard gates pass:

- structured-response success rate >= 99%;
- clinically critical field accuracy >= 97%;
- no unresolved catastrophic medication/numeric failure;
- same patient-level held-out cases as all competing candidates;
- JSON Schema constrained decoding enabled;
- raw predictions retained for audit.

These thresholds are engineering gates, not clinical safety certification.

If no candidate passes, **do not select a winner**. Expand/fix the benchmark or retain the current baseline while investigating failures.

---

## What counts as catastrophic

Examples include:

- `5.2` becoming `52`;
- `162 mg/dL` becoming `126 mg/dL`;
- `10 mg` becoming `100 mg`;
- `discontinued` becoming `continued`;
- a negated condition becoming an active diagnosis;
- a historical medication becoming current;
- a missing observation being hallucinated;
- an observation assigned to the wrong patient/document/date.

A model with a good average F1 but a catastrophic failure pattern must not win on average score alone.

---

## How to decide whether `olmOCR` stays

The question is not whether `olmOCR` has the lowest raw CER.

Compare complete pipeline outcomes:

```text
native text -> extraction model
RapidOCR    -> extraction model
olmOCR      -> extraction model
native-first -> fallback OCR -> extraction model
```

For each, measure:

- clinical numeric accuracy;
- critical field accuracy;
- structured extraction accuracy;
- extraction failure rate;
- end-to-end latency;
- peak resource use;
- per-document cost/latency.

If native text is sufficient on digital PDFs, it should remain the first path. If RapidOCR is sufficient for scans/photos, `olmOCR` should not be invoked merely because it exists. If `olmOCR` recovers critical information that lighter methods consistently lose, retain it as a targeted fallback and document the trigger condition.

The benchmark must therefore report both **quality** and **incremental value**.

---

## JSON Schema requirement details

The extraction request uses the Ollama `/api/chat` endpoint with:

```json
{
  "format": <PHIRE extraction JSON Schema>,
  "stream": false,
  "keep_alive": 0,
  "options": {
    "temperature": 0
  }
}
```

`format` is the critical part. It constrains the model's output grammar to the declared JSON Schema.

`keep_alive: 0` is intentional for model-selection runs because PHIRE's current GPU is shared by multiple local ML components. Keeping one candidate resident can contaminate the resource comparison and cause avoidable VRAM pressure.

The benchmark runs candidates sequentially for the same reason.

---

## Reporting model efficiency

For every candidate report:

- model tag;
- parameter class if known;
- quantization if known;
- model file size if known;
- peak VRAM;
- peak system RAM;
- cold load time;
- warm latency;
- p50 latency;
- p95 latency;
- output token count;
- documents/minute;
- extraction critical-field accuracy;
- entity F1;
- false-positive entity count;
- schema failure rate.

A smaller model wins only when its quality is acceptable and the resource improvement is meaningful.

---

## Final decision categories

The experiment should end with exactly one of these engineering decisions for the evaluated corpus:

### A. Keep Qwen3.5-9B

Use when smaller candidates fail a hard quality/safety gate.

### B. Replace with a smaller extraction model

Use when a smaller candidate passes the same quality gates and provides a meaningful resource/latency improvement.

### C. Unify extraction and generation around MedGemma

Use only if the tested MedGemma version matches extraction requirements without introducing unacceptable false positives or medication-status errors.

### D. Use a dedicated extractor

Use when a specialized extraction model materially outperforms the general medical LLM on structured extraction.

### E. Remove or demote `olmOCR`

Use when native text or lighter OCR is sufficient across the target document distribution.

### F. Retain `olmOCR` as a targeted fallback

Use when it provides measurable recovery on hard scanned/photographed cases but is unnecessary for easier documents.

---

## Research integrity rules

- Do not tune prompts separately for each model after seeing test results.
- Use one extraction prompt and one schema for the primary comparison.
- Record exact model tags and quantization.
- Record Ollama version and hardware.
- Record benchmark commit SHA.
- Do not mix training/development patients with held-out test patients.
- Do not randomly split documents from the same patient across train/test.
- Preserve raw model outputs.
- Report failures, not only aggregate scores.
- Run at least one repeated run for latency/resource measurements if the hardware is noisy.
- Use deterministic scoring for exact clinical fields.
- Clinician-review any safety-critical end-to-end conclusion.

---

## Interpretation rule

The benchmark is a **model and architecture selection experiment**, not a medical-device validation study and not evidence that any model is clinically safe for independent diagnosis or treatment.
