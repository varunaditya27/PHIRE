"""
VisionExtractor: local, layout-agnostic lab-report extraction via a local
Ollama vision model (qwen2.5vl by default) -- replaces the datalab-to/lift
VLM path (ml/rag/ingest/lift_extractor.py), which needed a 9.7B model
loaded in-process and had no working Apple GPU path. Ollama manages its
own GPU/Metal acceleration on Apple Silicon, so nothing here has to pick
a device.

Two model calls per document, not per page:
  1. Extraction -- transcribe every marker/medication/condition from all
     page images at once, strict "copy what's printed" rules.
  2. Verification -- send the same images back with pass 1's output and
     have the model audit it; can correct or remove entries but never
     invent new ones (enforced server-side below, not just by the prompt).

Output is shaped to ml.rag.ingest.lift_schema.CLINICAL_DOCUMENT_SCHEMA so
the rest of the ingestion pipeline (document_processor.py, ml/graph/*)
needs no changes.
"""

import base64
import json
import os
import re
from pathlib import Path
from typing import Any

import requests

from ml.local_only import require_localhost
from ml.rag.ingest.lift_schema import validate_lift_payload

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".webp"})

DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_VISION_MODEL", "qwen2.5vl:7b")

_VALUE_RE = re.compile(r"^-?\d{1,3}(?:,\d{3})*(?:\.\d+)?$|^-?\d+(?:\.\d+)?$")

_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "is_lab_report": {"type": "boolean"},
        "document_date": {"type": "string"},
        "markers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "string"},
                    "unit": {"type": "string"},
                },
                "required": ["name", "value"],
            },
        },
        "medications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "dosage": {"type": "string"},
                    "frequency": {"type": "string"},
                    "status": {"type": "string"},
                },
                "required": ["name"],
            },
        },
        "conditions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "status": {"type": "string"},
                },
                "required": ["name"],
            },
        },
    },
    "required": ["is_lab_report", "markers"],
}

_VERIFICATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "markers": _EXTRACTION_SCHEMA["properties"]["markers"],
    },
    "required": ["markers"],
}

_EXTRACTION_PROMPT = """\
You are a medical-records transcriptionist. Transcribe every lab marker \
visible in these page images, exactly as printed. Follow these rules \
strictly:

1. Copy each test name, measured value, and unit exactly as printed -- \
no unit conversion, no inferred units.
2. Never output a reference/normal range as the value.
3. Skip qualitative results, comments, demographics, headers/footers.
4. Omit any marker if a digit is unreadable or uncertain -- do not guess.
5. Also list any medications and conditions/diagnoses mentioned, and the \
report's own date if printed.
6. If these pages are not a lab report at all, return is_lab_report: \
false with an empty markers list.

Return only JSON matching the given schema."""

_VERIFICATION_PROMPT_TEMPLATE = """\
You are auditing a medical transcription for safety. Here are the same \
page images and a first-pass transcription of its lab markers:

{markers_json}

Check each marker character-by-character against the images:
- Correct any wrong value or unit.
- Remove any marker not actually present, or that is ambiguous/unreadable.
- Do NOT add any marker that is not already in this list.

Return only JSON matching the given schema, with the corrected markers list."""


class VisionExtractor:
    """Extracts structured clinical data from PDFs/images via a local Ollama vision model."""

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        mock: bool | None = None,
        timeout: float = 180.0,
    ) -> None:
        self.model = model or DEFAULT_MODEL
        self.host = host or DEFAULT_HOST
        require_localhost(self.host)
        self.timeout = timeout
        self.mock = (
            mock
            if mock is not None
            else (os.environ.get("PHIRE_MOCK_LIFT", "").lower() in ("1", "true", "yes"))
        )

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in SUPPORTED_EXTENSIONS

    def extract(self, file_path: Path) -> dict[str, Any]:
        if not self.supports(file_path):
            raise ValueError(f"Unsupported file format {file_path.suffix} for vision extraction.")
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        if self.mock:
            return self._generate_mock_payload()

        images = self._rasterize(file_path)

        pass1 = self._chat(_EXTRACTION_PROMPT, images, _EXTRACTION_SCHEMA)
        markers = pass1.get("markers") or []
        original_names = {_normalize_name(m.get("name", "")) for m in markers if isinstance(m, dict)}

        if markers:
            verify_prompt = _VERIFICATION_PROMPT_TEMPLATE.format(markers_json=json.dumps(markers))
            pass2 = self._chat(verify_prompt, images, _VERIFICATION_SCHEMA)
            verified = pass2.get("markers") or []
            # Defense against the model inventing new markers during
            # verification: it may only correct/remove entries from pass 1,
            # so anything whose name wasn't already there gets dropped.
            markers = [
                m for m in verified
                if isinstance(m, dict) and _normalize_name(m.get("name", "")) in original_names
            ]

        markers = _postprocess_markers(markers)

        payload = {
            "document_date": pass1.get("document_date"),
            "document_type": "Lab Report" if pass1.get("is_lab_report") else None,
            "observations": [
                {"name": m["name"], "value": m["value"], "unit": m.get("unit")}
                for m in markers
            ],
            "medications": pass1.get("medications") or [],
            "conditions": pass1.get("conditions") or [],
            "narrative_sections": [],
        }
        return validate_lift_payload(payload)

    def _rasterize(self, file_path: Path) -> list[str]:
        """Return base64-encoded PNG bytes for every page (PDF) or the image itself."""
        if file_path.suffix.lower() == ".pdf":
            import pymupdf

            images = []
            with pymupdf.open(file_path) as doc:
                for page in doc:
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))  # ~150 DPI
                    images.append(base64.b64encode(pix.tobytes("png")).decode())
            return images
        return [base64.b64encode(file_path.read_bytes()).decode()]

    def _chat(self, prompt: str, images: list[str], schema: dict[str, Any]) -> dict[str, Any]:
        """Call Ollama's /api/chat with images, retrying only transient connection errors."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt, "images": images}],
            "format": schema,
            "stream": False,
            "options": {"temperature": 0},
        }

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                response = requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
                response.raise_for_status()
                content = response.json()["message"]["content"]
                return json.loads(content)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                last_exc = exc
                continue
        raise RuntimeError(f"Ollama vision call failed after retries: {last_exc}") from last_exc

    def _generate_mock_payload(self) -> dict[str, Any]:
        return validate_lift_payload({
            "document_date": None,
            "document_type": "Diagnostic Laboratory Report",
            "observations": [
                {"name": "LDL Cholesterol", "value": "162", "unit": "mg/dL"},
                {"name": "HDL Cholesterol", "value": "48", "unit": "mg/dL"},
                {"name": "Fasting Blood Glucose", "value": "104", "unit": "mg/dL"},
            ],
            "medications": [
                {"name": "Atorvastatin", "dosage": "20 mg", "frequency": "once daily at bedtime", "status": "started"},
            ],
            "conditions": [
                {"name": "Hyperlipidemia", "status": "active"},
                {"name": "Impaired Fasting Glucose", "status": "active"},
            ],
            "narrative_sections": [],
        })


def _normalize_name(name: str) -> str:
    return name.strip().rstrip(":").lower()


def _postprocess_markers(markers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize names, validate/clean numeric values, and dedupe."""
    seen: set[tuple[str, str]] = set()
    cleaned: list[dict[str, Any]] = []
    for marker in markers:
        if not isinstance(marker, dict):
            continue
        name = marker.get("name")
        value = marker.get("value")
        if not name or value is None:
            continue

        name = str(name).strip().rstrip(":")
        value = str(value).strip()
        if _VALUE_RE.match(value):
            value = value.replace(",", "")

        key = (name.lower(), value)
        if key in seen:
            continue
        seen.add(key)

        cleaned.append({"name": name, "value": value, "unit": marker.get("unit")})
    return cleaned
