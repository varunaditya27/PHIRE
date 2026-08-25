"""
Router candidates: RapidOCR (in-process, pip-only) vs Surya OCR (needs a
separate vLLM/Docker or llama.cpp model-serving process) — see RESULTS.md
for why only RapidOCR has a working live candidate here.

Unlike ml/rag/ingest/experiments/candidates.py (which benchmarks
*extraction* quality for the production OCR path), this measures a
*router*'s job: fast, cheap, good enough to decide "does pypdf's text
layer look right, or does this page need the real olmOCR pass" — so
latency and confidence signal matter as much as raw accuracy.
"""

import time
from pathlib import Path

from rapidocr_onnxruntime import RapidOCR


class RapidOCRCandidate:
    """Wraps RapidOCR's per-line detections into a page transcription + confidence score."""

    def __init__(self) -> None:
        self.name = "RapidOCR"
        self._engine = RapidOCR()

    def run(self, image_path: Path) -> dict:
        """Return {text, confidence, latency_seconds} for one page image.

        confidence is the mean per-line recognition confidence RapidOCR
        reports — the signal a router would threshold on to decide
        whether to trust this page's cheap OCR read at all.
        """
        start = time.time()
        result, _ = self._engine(str(image_path))
        latency = time.time() - start
        if not result:
            return {"text": "", "confidence": 0.0, "latency_seconds": latency}
        lines = [line for _, line, _ in result]
        confidences = [conf for _, _, conf in result]
        return {
            "text": "\n".join(lines),
            "confidence": sum(confidences) / len(confidences),
            "latency_seconds": latency,
        }
