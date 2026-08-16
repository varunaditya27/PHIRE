"""
OCR model candidates: olmOCR v1 vs v2, at Q4_K_M vs Q8_0 quantization,
run locally via Ollama's vision API (see RESULTS.md for shortlist
rationale and pull commands).

Reuses the prompt, response schema, and response-parsing logic from
ml/rag/ingest/ocr.py (the production OCRTextExtractor this benchmark's
winner feeds) rather than a parallel copy — so this benchmark exercises
the same code path production runs, not a fork of it that could drift.
Only the model tag varies per candidate; production only ever uses one
(the winner).
"""

import base64
from pathlib import Path

import requests

from ml.rag.ingest.ocr import OCR_PROMPT, OLLAMA_HOST, RESPONSE_SCHEMA, extract_text_from_response


class OllamaVisionOCRCandidate:
    """Runs one Ollama-hosted vision model against a page image via /api/generate."""

    def __init__(self, name: str, model_tag: str) -> None:
        self.name = name
        self.model_tag = model_tag

    def extract(self, image_path: Path) -> str:
        image_b64 = base64.b64encode(image_path.read_bytes()).decode()
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": self.model_tag,
                "prompt": OCR_PROMPT,
                "images": [image_b64],
                "stream": False,
                "format": RESPONSE_SCHEMA,
                "options": {"temperature": 0.0},
            },
            timeout=300,
        )
        response.raise_for_status()
        return extract_text_from_response(response.json()["response"])


# (name, factory) pairs, consistent with ml/rag/experiments and
# ml/claims/experiments — built lazily so run_benchmark.py controls when
# each Ollama model actually gets invoked.
CANDIDATE_FACTORIES = [
    ("olmOCR-v1 (7B-0225-preview, Q4_K_M)", lambda: OllamaVisionOCRCandidate(
        "olmOCR-v1 (7B-0225-preview, Q4_K_M)", "hf.co/bartowski/allenai_olmOCR-7B-0225-preview-GGUF:Q4_K_M",
    )),
    ("olmOCR-v1 (7B-0225-preview, Q8_0)", lambda: OllamaVisionOCRCandidate(
        "olmOCR-v1 (7B-0225-preview, Q8_0)", "hf.co/bartowski/allenai_olmOCR-7B-0225-preview-GGUF:Q8_0",
    )),
    ("olmOCR-v2 (2-7B-1025, Q4_K_M)", lambda: OllamaVisionOCRCandidate(
        "olmOCR-v2 (2-7B-1025, Q4_K_M)", "hf.co/bartowski/allenai_olmOCR-2-7B-1025-GGUF:Q4_K_M",
    )),
    ("olmOCR-v2 (2-7B-1025, Q8_0)", lambda: OllamaVisionOCRCandidate(
        "olmOCR-v2 (2-7B-1025, Q8_0)", "hf.co/bartowski/allenai_olmOCR-2-7B-1025-GGUF:Q8_0",
    )),
]
