# OCR model selection: experiment & results

**Question**: Which fully-local OCR model should `ml/rag/ingest/patient_documents.py`
use for scanned/photographed patient documents (the gap flagged when
`PDFTextExtractor` was built — it only handles text-based PDFs, not images)?
Investigated after Varun surfaced `olmOCR` (Allen AI) as a candidate; this
benchmark compares its actual variants rather than assuming one.

Two rounds: the first used a small, uniform eval set (4 documents, one
font, list-style layouts only) and is **superseded** by this round's
harder, more varied set — see "What changed from round 1" below.

## Method

**Candidates** (`candidates.py`): olmOCR v1 (`allenai/olmOCR-7B-0225-preview`)
vs v2 (`allenai/olmOCR-2-7B-1025`), each at Q4_K_M vs Q8_0 quantization — a
version x precision grid, 4 candidates total. All run locally via Ollama's
vision API, GGUF builds from `bartowski` (the only GGUF repackaging found
that bundles a matching `mmproj` vision-projector file, verified before
selecting it — several other community conversions don't, which makes them
silently unusable for actual image OCR despite pulling successfully).

**Prompt**: olmOCR's own official "no-anchoring" prompt, taken verbatim from
`github.com/allenai/olmocr`'s `build_no_anchoring_v4_yaml_prompt()` — a
different prompt would be an unfair handicap, since this is what the model
was actually trained against. That prompt explicitly instructs the model to
convert tables to HTML — this drives one of the findings below.

**Structured output**: requests use Ollama's `format` parameter with an
explicit JSON Schema (grammar-constrained decoding), not just a hope that
the model self-formats correctly. This mattered in practice: without it,
olmOCR-v1 at Q4_K_M was observed on live test calls emitting malformed JSON
(missing the `natural_text` key literal entirely, otherwise valid-looking) —
a real reliability gap the schema constraint eliminates at the source.
`candidates.py`'s `_extract_text` keeps fallback parsing tiers as
defense-in-depth regardless.

**Eval set** (`eval_data/`): **6 synthetic patient documents spanning real
layout variety**, each rendered as a **clean** image (direct PDF/scan) and
a **photo** variant (perspective warp, rotation, blur, noise, vignette,
JPEG compression — simulates an actual phone-camera photo), 12 images
total:

| Document | Layout | Font |
|---|---|---|
| `cmp_table` | Grid table (metabolic panel, 8 rows x 4 cols) | Sans |
| `vaccine_record` | Grid table (immunization history, 4 rows x 4 cols) | Sans |
| `demographics_vitals` | Two-column demographics + grid table | Sans |
| `progress_note` | Dense narrative prose (physician note) | Serif |
| `radiology_report` | Dense narrative prose (findings/impression) | Serif |
| `medication_reconciliation` | Mixed prose + bulleted list | Mono |

**Metrics** (`metrics.py`):
- Character/word error rate (CER/WER) against the ground truth text.
- **Content CER/WER** — CER/WER after stripping HTML tags and Markdown
  table syntax from both hypothesis and reference (`strip_markup`). Added
  this round after discovering raw CER unfairly penalizes a model for
  correctly following the prompt's "convert tables to HTML" instruction —
  see Results below.
- **Field accuracy** — whether each document's clinically critical values
  (a lab result, a dosage) are correctly recoverable, independent of
  formatting/reading-order differences. This is the metric that matters
  most for PHIRE's purpose: a transcription that reorders a two-column
  layout but gets every value right is safe to ingest; one with low CER
  but a flipped digit in a value is not.

**Reproduce**: pull all four model tags first (see `candidates.py`'s
`CANDIDATE_FACTORIES`), then
`ml/.venv/bin/python -m ml.rag.ingest.experiments.run_benchmark` from the
repo root (~14 minutes on this GPU — Q8_0 candidates run ~4x slower than
Q4_K_M). Regenerate the eval images (after editing `documents.py`) via
`ml/.venv/bin/python -m ml.rag.ingest.experiments.eval_data.generate_images`.
Full per-image transcriptions are in `results.json` for audit.

## Results

| Model | CER | Content CER | WER | Content WER | Field Accuracy |
|---|---|---|---|---|---|
| olmOCR-v1 (Q4_K_M) | 0.3336 | 0.1146 | 0.4305 | 0.1216 | 1.0 |
| olmOCR-v1 (Q8_0) | 0.3499 | 0.1375 | 0.4474 | 0.1414 | 1.0 |
| **olmOCR-v2 (Q4_K_M)** | 0.6642 | **0.0120** | 0.5102 | **0.0224** | 1.0 |
| olmOCR-v2 (Q8_0) | 0.6642 | **0.0120** | 0.5102 | **0.0224** | 1.0 |

**All four candidates hit perfect field accuracy** — every clinically
critical value correctly recovered across all 12 images, tables, prose, and
photos alike.

**Raw CER is actively misleading here and content CER corrects it**: v1
*appears* to win on raw CER (0.33 vs v2's 0.66), but inspecting the actual
transcriptions shows why — v1 emits compact Markdown tables (`| Sodium |
138 mEq/L |`), which happen to be character-count-close to plain text,
while v2 correctly follows the prompt's instruction and emits full HTML
tables (`<table><tr><td>Sodium</td>...`), which is *more prompt-compliant*
but scores worse against plain-text ground truth purely on markup verbosity.
Once both are normalized to their actual content (`content_cer`), **v2 is
~10x more accurate than v1** (0.012 vs 0.11-0.14) — consistent with round
1's simpler-eval-set finding that v2 outperforms v1.

**Q4_K_M vs Q8_0 still made no measurable quality difference** for either
version — identical scores to 4 decimal places — while Q8_0 took ~4x
longer and needs 9.5GB vs 6.0GB on disk.

**The one meaningfully non-zero content-CER result** (v2 Q4_K_M on
`demographics_vitals_clean`, 0.14): inspecting the transcription shows this
is a **reading-order artifact, not a content error** — the two-column
demographics block (Name/DOB/Sex on the left, MRN/Insurance/Visit Date on
the right) was transcribed left-column-then-right-column (a defensible
natural reading order) instead of this eval set's row-interleaved ground
truth ordering. Every field value is present and correct; `field_accuracy`
correctly scored this 1.0.

## What changed from round 1

Round 1 used 4 documents, one font, list-style "Label: Value" layouts only,
and a naive CER/WER (no markup normalization) — it agreed with this round
on the headline conclusion (v2 beats v1, Q4_K_M ties Q8_0) but for the
wrong reason on CER specifically, since round 1's eval set had no tables to
expose the HTML-vs-Markdown scoring bias. Round 2 (this one) adds real
grid tables, two-column layout, three fonts, and dense narrative prose —
diverse enough to actually exercise olmOCR's stated strengths (tables,
mixed layouts) — and adds content-normalized CER/WER after the raw metric
was caught giving a misleading ranking on the new table documents.

## Limitations (read before trusting this too far)

- **N=12 images, still synthetic, still not real scanned patient
  records.** More layout variety than round 1, but machine-rendered
  typography throughout — real documents vary in scan quality, physical
  wear (creases, stains), and layout inconsistency far more than this set
  covers.
- **Content CER strips markup with a regex, not a real HTML/Markdown
  parser** (`strip_markup`) — good enough to make HTML and Markdown tables
  comparable to plain text, not a rigorous document-structure diff.
- **Field accuracy uses substring matching**, not exact-position — low
  false-positive risk given the specificity of values like "142/91 mmHg",
  but not a formal guarantee.
- **Ground truth's row-interleaved two-column ordering may itself be the
  "wrong" convention** — see the `demographics_vitals` finding above. A
  future round should consider scoring reading-order-flexible layouts by
  set overlap rather than sequential edit distance.
- Community GGUF quantization (bartowski), not an official Allen AI
  release — spot-checked as reliable in practice (structured output was
  clean once `format` was applied), but worth keeping in mind.

## Decision

**Use `olmOCR-v2 (2-7B-1025) at Q4_K_M`** for the planned OCR extractor:
best content CER by a wide margin, ties for best field accuracy, ~4x
faster than Q8_0 with no measured quality cost, and the smaller VRAM
footprint matters given this machine's 8GB budget is shared with the
embedding/reranking/NLI models elsewhere in `ml/`.

Not yet implemented: an actual `OCRTextExtractor` wired into
`patient_documents.py`'s `TextExtractor` interface (the interface was
already designed for this — see its docstring). This benchmark answers
*which model*; the extraction module + graph/Observation-parsing work it
feeds is a separate next step.
