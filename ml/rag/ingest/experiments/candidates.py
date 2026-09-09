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
import json
import os
import re
from pathlib import Path

import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

OCR_PROMPT = (
    "Attached is one page of a document that you must process. Just return the "
    "plain text representation of this document as if you were reading it "
    "naturally. Convert equations to LateX and tables to HTML.\n"
    "If there are any figures or charts, label them with the following markdown "
    "syntax ![Alt text describing the contents of the figure]"
    "(page_startx_starty_width_height.png)\n"
    "Return your output as markdown, with a front matter section on top "
    "specifying values for the primary_language, is_rotation_valid, "
    "rotation_correction, is_table, and is_diagram parameters."
)

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "primary_language": {"type": "string"},
        "is_rotation_valid": {"type": "boolean"},
        "rotation_correction": {"type": "integer"},
        "is_table": {"type": "boolean"},
        "is_diagram": {"type": "boolean"},
        "natural_text": {"type": "string"},
    },
    "required": ["natural_text"],
}

_FRONT_MATTER_RE = re.compile(r"^---.*?---\s*", re.DOTALL)
_QUOTED_STRING_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def extract_text_from_response(raw_response: str) -> str:
    try:
        parsed = json.loads(raw_response)
        if isinstance(parsed, dict) and "natural_text" in parsed:
            return (parsed["natural_text"] or "").strip()
    except json.JSONDecodeError:
        pass

    if raw_response.lstrip().startswith("---"):
        return _FRONT_MATTER_RE.sub("", raw_response, count=1).strip()

    quoted = _QUOTED_STRING_RE.findall(raw_response)
    if quoted:
        longest = max(quoted, key=len)
        for escaped, literal in (('\\n', '\n'), ('\\t', '\t'), ('\\"', '"'), ('\\\\', '\\')):
            longest = longest.replace(escaped, literal)
        return longest.strip()

    return raw_response.strip()


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
