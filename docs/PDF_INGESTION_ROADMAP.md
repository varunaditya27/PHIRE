# Patient PDF ingestion router design (historical — superseded, never built)

> [!NOTE]
> **SUPERSEDED AS OF 2026-09-09**: This multi-stage router design (pypdf + RapidOCR agreement check + olmOCR-v2 fallback) was formally superseded by the adoption of `datalab-to/lift` (9.7B parameter VLM).
> `datalab-to/lift` performs unified, single-pass visual document extraction directly from both digital and scanned PDFs as well as image files, rendering OCR disagreement routing obsolete. On machines without a CUDA GPU, extraction uses an Ollama vision model instead (`ml/rag/ingest/ollama_extractor.py`, see [CPU_SETUP.md](CPU_SETUP.md)). See [docs/superpowers/specs/2026-09-09-lift-vlm-ocr-integration-design.md](superpowers/specs/2026-09-09-lift-vlm-ocr-integration-design.md) for the active architecture.

**Status**: Historical reference / superseded.

---

## 1. The gap

`ml/rag/ingest/patient_documents.py`'s `PDFTextExtractor` only handles
text-based PDFs (embedded text layer). Two real failure modes fall through
uncaught today:

1. **A scanned PDF** (image content, no text layer) — `pypdf` returns empty
   text, `extract_text()` raises. `OCRTextExtractor` (olmOCR-v2, already
   built) could handle the *content* fine, but it only accepts raw image
   formats (`.jpg`/`.png`/`.webp`) — a `.pdf` never reaches it, regardless
   of what's actually inside the file.
2. **A PDF with a broken text-layer encoding** — a custom `/Differences`
   font mapping can make `pypdf` return non-empty but *wrong* text (real,
   documented pypdf/PyMuPDF bug reports — glyph codes decoded through the
   wrong table). This is worse than the empty case: it looks like a
   successful extraction and would silently index garbage.

## 2. Decided design (not yet implemented)

**Router, not a full second extraction pass.** A cheap OCR pass classifies
whether pypdf's output can be trusted, rather than either (a) a
character-heuristic gate on pypdf's own output, or (b) always paying for
the expensive olmOCR pass regardless of pypdf's success.

Pipeline, per PDF page:

1. Rasterize the page to an image (PyMuPDF/`fitz` — not yet a project
   dependency, needs adding).
2. Run RapidOCR on the rasterized image (fast, CPU-only, in-process —
   benchmarked in `ml/rag/ingest/router_experiments/RESULTS.md`).
3. **Compare RapidOCR's read against pypdf's text for that page** — not
   RapidOCR's self-reported confidence score alone. The router benchmark
   found confidence doesn't discriminate correct from incorrect reads (0.98
   mean confidence on clean images vs. 0.95 on degraded ones, despite field
   accuracy collapsing 0.89 → 0.25 between them) — but two independent
   extractions of the same page disagreeing is a real signal either one is
   wrong, even when neither system knows it.
4. If they substantially agree, trust pypdf (fast, exact, already the
   common case). If they disagree, or pypdf's output was empty to begin
   with, route that page's rasterized image through the existing
   `OCRTextExtractor` (olmOCR-v2) for the real transcription.

This closes gap #1 (empty pypdf output always routes to olmOCR) and gap #2
(wrong-but-nonempty pypdf output gets caught by the disagreement check,
where a character-plausibility heuristic on pypdf's output alone couldn't
catch it — the corruption can produce technically valid, printable, wrong
text, not just garbage).

## 3. Why RapidOCR, not Surya OCR, not a text heuristic alone

Full comparison and live benchmark: `ml/rag/ingest/router_experiments/RESULTS.md`.

- **A pure character/n-gram heuristic gate on pypdf's output** (considered
  first) can't reliably catch the "valid characters, wrong meaning" failure
  mode — the corrupted text can look structurally like real text. An
  independent second read of the actual pixels is needed, not more
  inference from the same corrupted string.
- **A lightweight OCR tool as router beats a full second heavy-model
  pass**: doesn't cost as much as unconditionally running olmOCR on every
  PDF, which would erase the fast path for the common case (a normal,
  correctly-encoded PDF).
- **Surya OCR was ruled out on infra weight, not accuracy.** Its current
  release needs a separate model-serving process (vLLM+Docker or a
  llama.cpp server) — both backends failed to even start on this machine
  (Docker permissions; then an unsupported model architecture in Fedora's
  packaged llama.cpp). A router needing its own serving daemon isn't
  lightweight by any definition that matters here.
- **RapidOCR was benchmarked live**, pip-installed, in-process, ~1.3s/page,
  CPU-only (no GPU contention with olmOCR or the embedding model), correct
  on 5/6 test documents on clean-rendered pages (the router's actual input
  shape — a rendered PDF page, not a degraded phone photo).

## 4. Not yet implemented

- `pymupdf` isn't in `ml/requirements.txt` yet — needed for page
  rasterization.
- No agreement/comparison function exists yet between RapidOCR's output and
  pypdf's per-page text (token-overlap/Jaccard similarity, or similar —
  not designed in detail yet, just the general shape).
- `PDFTextExtractor`/`extract_text()` in `patient_documents.py` isn't
  wired to attempt this router path — currently still a hard fail on empty
  pypdf output.
- `rapidocr-onnxruntime==1.4.4` **is** already pinned in
  `ml/requirements.txt` and installed in `ml/.venv` (added during the
  benchmark) — the router implementation can use it directly, no new
  install needed for that half.

## 5. Trigger to pick this back up

Any of: a real patient upload hits one of the two failure modes above in
practice; Anika's `/api/documents/upload` needs this gap closed before
shipping; or a dedicated ingestion-hardening pass gets scheduled.
