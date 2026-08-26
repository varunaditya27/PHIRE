"""
OCR-based text extraction for scanned/photographed patient documents, via
olmOCR-v2 run locally through Ollama.

Model choice is benchmarked, not assumed: content CER 0.012 vs olmOCR-v1's
0.11-0.14, perfect field-level accuracy for both — see
experiments/RESULTS.md. This is the canonical implementation of the
prompt/schema/parsing logic; experiments/candidates.py imports from here
so the benchmark exercises the same code this extractor runs, not a
parallel copy that could drift from it.
"""

import base64
import json
import os
import re
from pathlib import Path

import requests

from ml.local_only import require_localhost

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OCR_MODEL", "hf.co/bartowski/allenai_olmOCR-2-7B-1025-GGUF:Q4_K_M")
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

# Verbatim from allenai/olmocr's prompts.py (build_no_anchoring_v4_yaml_prompt)
# — this is the prompt olmOCR was actually trained against.
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

# Mirrors olmOCR's own front-matter fields so the schema doesn't fight the
# distribution the model was trained to produce. Grammar-constrained
# decoding (Ollama's `format`), not just a hope the model self-formats
# correctly — olmOCR-v1 at Q4_K_M was observed on live calls emitting
# malformed JSON without this (missing the "natural_text" key literal).
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
    """Pull the transcribed body out of olmOCR's response.

    Three fallback tiers, each observed live (not hypothetical) across
    checkpoints/quantizations:
    1. Well-formed JSON with a "natural_text" key (the normal case with
       RESPONSE_SCHEMA applied).
    2. YAML front matter + markdown body (a differently-formatted model
       response, in case a future model swap doesn't honor `format`).
    3. Malformed JSON missing the "natural_text" key literal entirely
       (seen from olmOCR-v1 at Q4_K_M without schema constraints). The
       longest quoted string in the response is almost certainly the
       transcription, not a short metadata value like "en" or "false".
    """
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


class OCRTextExtractor:
    """Extracts text from a scanned/photographed document image via a local vision-language model."""

    def __init__(self, model: str | None = None, host: str | None = None) -> None:
        self.model = model or DEFAULT_MODEL
        self.host = host or OLLAMA_HOST
        require_localhost(self.host)

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in SUPPORTED_SUFFIXES

    def extract(self, file_path: Path) -> str:
        image_b64 = base64.b64encode(file_path.read_bytes()).decode()
        response = requests.post(
            f"{self.host}/api/generate",
            json={
                "model": self.model,
                "prompt": OCR_PROMPT,
                "images": [image_b64],
                "stream": False,
                "format": RESPONSE_SCHEMA,
                # Unload the model from VRAM immediately after this call,
                # not Ollama's default ~5min keep-alive — this extractor
                # runs once per document, and the very next step
                # (HybridRetriever) needs to load MedCPT on the same 8GB
                # GPU right after. Verified live: without this, a single
                # ingest_patient_document.py run OOMs, since olmOCR stays
                # resident and leaves no headroom.
                "keep_alive": 0,
                "options": {"temperature": 0.0},
            },
            timeout=300,
        )
        response.raise_for_status()
        return extract_text_from_response(response.json()["response"])
