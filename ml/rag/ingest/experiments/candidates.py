"""
OCR model candidates: olmOCR v1 vs v2, at Q4_K_M vs Q8_0 quantization,
run locally via Ollama's vision API (see RESULTS.md for shortlist
rationale and pull commands).

Uses the official olmOCR "no-anchoring" prompt (from
github.com/allenai/olmocr's build_no_anchoring_v4_yaml_prompt) rather
than an ad-hoc one — this is the prompt olmOCR was actually trained
against, so a different prompt would be an unfair handicap, not a fair
comparison point.

Requests use Ollama's `format` parameter with an explicit JSON Schema
(grammar-constrained decoding), not just a hope that the model
self-formats its front matter correctly. This was worth doing, not just
convenient: without it, olmOCR-v1 at Q4_K_M was observed emitting
malformed JSON (missing the "natural_text" key literal, otherwise
valid-looking) on live test calls — a real reliability gap, not a
hypothetical one. _extract_text's fallback parsing tiers stay in place as
defense-in-depth for any candidate that doesn't honor `format` cleanly.
"""

import base64
import json
import os
import re
from pathlib import Path

import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# Verbatim from allenai/olmocr's prompts.py (build_no_anchoring_v4_yaml_prompt).
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

# Mirrors olmOCR's own front-matter fields (see OCR_PROMPT) so the schema
# doesn't fight the distribution the model was trained to produce.
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


def _extract_text(raw_response: str) -> str:
    """Pull the transcribed body out of olmOCR's response.

    Three fallback tiers, each observed live (not hypothetical) across
    checkpoints/quantizations:
    1. Well-formed JSON with a "natural_text" key.
    2. YAML front matter + markdown body.
    3. Malformed JSON missing the "natural_text" key literal entirely
       (seen from olmOCR-v1 at Q4_K_M — the model emits the transcription
       as a bare quoted string with no key name before it, otherwise
       valid-looking JSON). The longest quoted string in the response is
       almost certainly the transcription, not a short metadata value
       like "en" or "false" — recovering it is more useful than scoring
       the whole malformed blob as the transcription, which would
       overstate how wrong the actual OCR was for a JSON-formatting slip.
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
        # Only unescape JSON's own control sequences, not a full
        # unicode_escape decode — that assumes a latin-1-like byte
        # source and mangles any non-ASCII character in the transcription.
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
        return _extract_text(response.json()["response"])


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
