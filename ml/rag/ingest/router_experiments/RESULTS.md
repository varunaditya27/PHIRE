# OCR router selection: experiment & results

**Question**: for the planned fix to `patient_documents.py`'s scanned-PDF gap
(a PDF with no usable text layer falls through both `PDFTextExtractor` and
`OCRTextExtractor` today), what cheap, lightweight OCR tool should sit in
front of the expensive olmOCR pass to decide *whether a page needs it at
all*? Raised after Varun suggested a "secondary lightweight OCR tool to
classify the path" instead of a pure text-heuristic gate on pypdf's output —
this compares the two concrete candidates raised for that role: RapidOCR and
Surya OCR.

This is a **router** decision, not an extraction-quality decision — the
tool here never produces the text PHIRE actually indexes; it only decides
whether pypdf's output can be trusted or the page needs to go through
`OCRTextExtractor` (olmOCR-v2, already selected and benchmarked separately
in `../experiments/RESULTS.md`).

## Method

**Eval set**: reused as-is from `../experiments/eval_data/` — the same 12
images (6 synthetic patient documents x clean/photo variants) and ground
truth the olmOCR model-selection benchmark used, so these numbers are
directly comparable to that benchmark's. See that RESULTS.md for the eval
set's layout/font variety.

**Metrics** (`../experiments/metrics.py`, reused): CER, content-CER (markup
stripped), WER, content-WER, field accuracy — plus, new for this benchmark,
**latency** (wall-clock per page) and **self-reported confidence** (mean
per-detection confidence score), since a router's job is to be fast and to
know when it doesn't know, not to be maximally accurate.

**Candidates attempted**: RapidOCR (`rapidocr-onnxruntime`, pip-installed
into `ml/.venv`) and Surya OCR (`surya-ocr`, same). Only RapidOCR produced a
live run — see "Surya: could not get a live run" below for why, with the
actual failure output.

**Reproduce**: `ml/.venv/bin/python -m ml.rag.ingest.router_experiments.run_benchmark`
from the repo root. Full per-item output in `results.json`.

## Results: RapidOCR

| | CER | Content CER | WER | Content WER | Field Acc | Confidence | Mean Latency |
|---|---|---|---|---|---|---|---|
| All 12 images | 0.1304 | 0.0712 | 0.3866 | 0.3866 | 0.5694 | 0.9676 | 1.29s |
| **Clean only (6)** | — | 0.0447 | — | — | **0.8889** | 0.9818 | — |
| **Photo only (6)** | — | 0.0977 | — | — | **0.25** | 0.9533 | — |

**Clean-only numbers are the ones that matter for this router's actual job.**
A rendered PDF page (this router's real input) is a crisp digital image, not
a phone photo — it's structurally the "clean" variant, never "photo". On
clean images RapidOCR gets 5 of 6 documents to perfect field accuracy
(1.00), the sixth (`medication_reconciliation`, monospace font) to 0.33 —
inspecting its transcription shows genuine `0`/`o` character confusion
("Atorvastatin **4omg**" for "40mg", "Metformin **1ooomg**" for "1000mg")
plus one dropped line (the "Aspirin 81mg... discontinued" bullet vanished
entirely). Real errors, not formatting artifacts, but confined to one
font/layout combination out of six.

**RapidOCR's own confidence score is not a usable routing signal on its
own.** Field accuracy collapses from 0.89 (clean) to 0.25 (photo) — a 64-point
swing — while mean confidence drops only 0.98 → 0.95, a 3-point swing.
Concretely: `radiology_report_photo` scored **field_accuracy=0.00** at
**confidence=0.948**, nearly identical to `radiology_report_clean`'s
confidence=0.982 despite one being perfect and the other having lost content.
RapidOCR is confidently wrong on degraded input as often as it's confidently
right on clean input — its per-detection confidence reflects character-glyph
recognition certainty, not semantic/content correctness. **Implication for
the router design**: don't gate on RapidOCR's confidence threshold alone;
gate on *agreement between RapidOCR's read and pypdf's own text-layer
extraction* for the same page — two independent extractions disagreeing is a
real signal; one extraction being self-confident is not.

Latency: 1.29s mean per page (0.63s–1.83s range), CPU-bound (ONNXRuntime, no
GPU used) — negligible next to a single olmOCR call (multi-second, GPU,
competes for the same 8GB VRAM budget as the embedding model).

## Surya: could not get a live run

Surya OCR's current release (`surya-ocr` 0.22.1) is not the in-process
CRNN-style model its earlier reputation describes — it's now a generative
VLM served over HTTP by a separate backend process, either:

- **vLLM in Docker** (auto-selected on this machine — it has an NVIDIA GPU).
  Failed immediately: `docker run failed: permission denied while trying to
  connect to the docker API at unix:///var/run/docker.sock`.
- **llama.cpp's `llama-server`**, tried after installing `llama-cpp` via
  `dnf` (Fedora). The binary launched and downloaded Surya's model
  (`surya-2.gguf`, a custom hybrid Qwen3.5/SSM architecture, 1.18GB) without
  issue, but Fedora's packaged llama.cpp build doesn't yet support that
  architecture:
  ```
  llama_model_load: error loading model: error loading model architecture: unknown model architecture: 'qwen35'
  ```

Two independent backend paths, two independent infrastructure failures.
Getting a working Surya run would mean either fixing Docker permissions and
running a vLLM container per OCR call, or building llama.cpp from source at
a commit newer than Fedora's package — real effort for what's supposed to be
the *cheap, disposable* half of the pipeline. That infra weight is itself a
disqualifying data point for the router role, independent of accuracy: a
router that needs its own model-serving daemon isn't lightweight by any
definition that matters here, next to RapidOCR's plain `pip install` and
in-process CPU inference.

**Published (not independently verified) figures**, for context only: Surya
is reported at 83.3% accuracy on olmOCR-bench at 650M params, and 30-50%
lower CER than Tesseract on degraded/complex-layout documents (search
results, Aug 2026 — see chat history for sources). Believable given it's a
modern VLM-based architecture, but not confirmed against this project's own
eval set, and the accuracy question is secondary to the infra-weight finding
above for this specific role.

## Limitations

- N=12 images, same synthetic set as the olmOCR benchmark — same caveats
  apply (see `../experiments/RESULTS.md`'s Limitations section).
- RapidOCR's line-joining (`"\n".join(lines)` over per-box detections, see
  `candidates.py`) sometimes drops a space between two adjacent boxes on the
  same visual line (`"Cardiothoracicratio"` for `"Cardiothoracic ratio"`) —
  this is an artifact of this benchmark's naive text reconstruction, not a
  RapidOCR limitation; `field_accuracy`'s exact-substring matching penalizes
  it as a miss even though the content is present. A real router
  implementation doesn't need word-perfect reconstruction — only agreement
  with pypdf's text at a coarser granularity (see Decision) — so this
  doesn't change the recommendation, but it does mean the field-accuracy
  numbers above are a slight underestimate of RapidOCR's actual per-token
  correctness.
- Surya's failures are specific to this machine's software versions
  (Fedora's `llama-cpp` package version, Docker daemon permissions) — a
  different environment might get a working Surya run. Re-attempting is
  reasonable if RapidOCR's accuracy proves insufficient in practice, but
  isn't worth blocking on now.

## Decision

**Use RapidOCR** as the router's cheap OCR pass. It installs and runs
in-process with no new system-level infrastructure (fits `ml/`'s
uv-isolated, no-system-Python-touching convention the same way olmOCR's
Ollama dependency does), is fast (~1.3s/page, CPU-only, doesn't compete for
the 8GB GPU), and gets clean-rendered pages — this router's actual input —
right on 5 of 6 document/font combinations tested.

**Routing logic should compare RapidOCR's output against pypdf's, not
threshold RapidOCR's confidence alone** — confidence didn't discriminate
correct from incorrect reads in this benchmark, but two independent
extractions of the same page disagreeing is a real signal either one is
wrong.

Not yet implemented: the actual router wired into `patient_documents.py`
(PyMuPDF rasterization of PDF pages, the RapidOCR-vs-pypdf agreement check,
and the fallback into `OCRTextExtractor`) — this benchmark answers *which
tool*; the routing module is a separate next step.
