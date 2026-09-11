"""
GeminiExtractor: cloud vision-LLM extraction of lab reports via Gemini.

Layout-agnostic: every page is rendered to a high-resolution image (PDF)
or used as-is (PNG/JPG/WEBP) and read by the model, so the diagnostic
centre's report layout never matters. Two model calls per document
(extraction + verification), not per page.

SAFETY: values/units are transcribed verbatim, never converted or
inferred. The verification pass re-checks every marker against the page
images and can only correct or remove entries -- it can never introduce
a marker that wasn't in the first pass (enforced here, not just by the
prompt).

Adapted from a provided reference implementation to plug into this
repo's ingestion pipeline: output is shaped to
ml.rag.ingest.lift_schema.CLINICAL_DOCUMENT_SCHEMA (adds document_date/
medications/conditions to the original markers-only schema) so
document_processor.py and ml/graph/* need no changes.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from ml.rag.ingest.lift_schema import validate_lift_payload

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".webp"})

_IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

_VALUE_RE = re.compile(r"-?\d+(?:,\d{3})*(?:\.\d+)?")

# Gemini occasionally double-escapes a unicode character in its JSON output
# (writes the source characters `\` and `u00b5` instead of the actual µ),
# which is valid JSON -- json.loads has nothing to reject -- but leaves a
# literal "µ" sitting inertly in the parsed string. It's also
# inconsistent about it: sometimes the 4 hex digits get dropped entirely
# (a bare "\u" glued straight onto the next word), which no amount of
# regex can recover the original character from. Both cases produce a
# stray backslash that breaks any *later* JSON parsing this text flows
# into (ml/claims/extractor.py re-parses LLM output that may quote this
# text back) -- so well-formed escapes get decoded to the real character,
# and anything left over gets stripped as noise, generically for whatever
# field/symbol triggered it, not one hardcoded case.
_DOUBLE_ESCAPED_UNICODE_RE = re.compile(r"\\u([0-9a-fA-F]{4})")
_STRAY_BACKSLASH_U_RE = re.compile(r"\\u")


def _fix_double_escaped_unicode(value: Any) -> Any:
    if isinstance(value, str):
        fixed = _DOUBLE_ESCAPED_UNICODE_RE.sub(lambda m: chr(int(m.group(1), 16)), value)
        return _STRAY_BACKSLASH_U_RE.sub("", fixed)
    if isinstance(value, list):
        return [_fix_double_escaped_unicode(v) for v in value]
    if isinstance(value, dict):
        return {k: _fix_double_escaped_unicode(v) for k, v in value.items()}
    return value

# Same shape as the reference implementation's MARKER_SCHEMA, plus
# document_date/medications/conditions so the rest of this app's pipeline
# (graph facts, medications list, conditions list) keeps working.
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
                    "reference_range": {"type": "string"},
                    "interpretation": {"type": "string"},
                },
                "required": ["name", "value", "unit"],
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
        "is_lab_report": {"type": "boolean"},
        "markers": _EXTRACTION_SCHEMA["properties"]["markers"],
    },
    "required": ["is_lab_report", "markers"],
}

_EXTRACTION_PROMPT = """You are a medical-records transcriptionist. The attached image(s) are pages of a laboratory blood test report. Transcribe every blood/lab test marker that has a measured numeric result.

STRICT RULES — patient safety depends on exact transcription:
1. Copy the test NAME, the measured VALUE and the UNIT exactly as printed on the page. Do NOT convert units, do NOT normalize values, do NOT infer a unit that is not printed. If no unit is printed for a test, use an empty string for unit.
2. The VALUE is the patient's measured result, NOT the reference/normal range. Reference ranges usually look like "12.0 - 15.0" or "Up to 40". Never output a range as the value.
3. Only include tests where a numeric measured result is visible. Skip qualitative results (e.g. "Negative", "Normal"), comments, methods, doctor names, patient demographics, page headers/footers.
4. Include calculated values (e.g. ratios, indices) only if they appear as results in the report.
5. If a value is unreadable or you are not fully certain of any digit, OMIT that marker entirely rather than guessing.
6. If the pages are not a lab report at all, set is_lab_report to false and return an empty markers list.
7. If the report prints a reference/normal range for a marker, copy it exactly into reference_range (e.g. "70 - 100", "< 5.7"). If it prints a flag/interpretation for that marker (e.g. "High", "Low", "Normal", "H", "L"), copy it exactly into interpretation. Leave either empty if not printed -- do not calculate or infer one yourself.
8. Also list any medications and diagnosed conditions mentioned, and the report's own printed date (document_date), if present.

Return JSON matching the required schema. "value" must be the exact printed number as a string (keep decimals exactly as printed)."""

_VERIFICATION_PROMPT_TEMPLATE = """You are auditing a transcription of the attached lab report page(s) for medical safety. Below is a JSON list of markers that were transcribed from these exact pages.

For EACH marker, find it on the page and check character-by-character that the value, unit, reference_range, and interpretation match what is printed.
- If a marker is correct, keep it unchanged.
- If a value, unit, reference_range, or interpretation was mis-transcribed, output the corrected field exactly as printed.
- If a marker does not actually appear on the pages, or its printed value is ambiguous/unreadable, REMOVE it.
- Do NOT add any new markers, and do NOT invent a reference_range or interpretation that isn't printed.

Transcription to audit:
{markers_json}

Return JSON matching the required schema (is_lab_report=true, markers = the audited list)."""


class GeminiExtractor:
    """Extracts structured clinical data from PDFs/images via Gemini's vision API."""

    def __init__(self, api_key: str | None = None, model: str | None = None, mock: bool | None = None) -> None:
        api_key = (api_key or os.environ.get("GEMINI_API_KEY", "")).strip()
        self.api_key_configured = bool(api_key)
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.mock = (
            mock
            if mock is not None
            else (os.environ.get("PHIRE_MOCK_LIFT", "").lower() in ("1", "true", "yes"))
        )
        self._client = None
        self._api_key = api_key

    def _get_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in SUPPORTED_EXTENSIONS

    def extract(self, file_path: Path) -> dict[str, Any]:
        if not self.supports(file_path):
            raise ValueError(f"Unsupported file format {file_path.suffix} for Gemini extraction.")
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        if self.mock:
            return self._generate_mock_payload()

        if not self.api_key_configured:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured -- set it in backend/.env to enable real extraction."
            )

        images = self._load_page_images(file_path)
        if not images:
            raise RuntimeError(f"Could not read any pages from {file_path}")

        pass1 = self._call_model(images, _EXTRACTION_PROMPT, _EXTRACTION_SCHEMA)
        if not pass1.get("is_lab_report", False):
            return validate_lift_payload({
                "document_date": None, "document_type": None,
                "observations": [], "medications": [], "conditions": [], "narrative_sections": [],
            })

        markers = pass1.get("markers") or []
        if markers:
            markers = self._verification_pass(images, markers)

        markers = self._finalize(markers)

        payload = {
            "document_date": pass1.get("document_date") or None,
            "document_type": "Lab Report",
            "observations": [
                {
                    "name": m["test"],
                    "value": m["result"],
                    "unit": m.get("unit") or None,
                    "reference_range": m.get("reference_range") or None,
                    "interpretation": m.get("interpretation") or None,
                }
                for m in markers
            ],
            "medications": pass1.get("medications") or [],
            "conditions": pass1.get("conditions") or [],
            "narrative_sections": [],
        }
        return validate_lift_payload(payload)

    def _load_page_images(self, file_path: Path) -> list[dict[str, Any]]:
        """Render every PDF page to a high-res PNG, or load an image as-is.

        Returns a list of {"mime_type", "data"} dicts rather than SDK
        Part objects directly, so this module doesn't need the SDK
        imported at module load time (keeps mock mode/import-time cost
        cheap, matching the rest of ml/'s extractors).
        """
        ext = file_path.suffix.lower()
        parts: list[dict[str, Any]] = []

        if ext == ".pdf":
            import pymupdf

            with pymupdf.open(file_path) as doc:
                for page in doc:
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))  # ~150 DPI
                    parts.append({"mime_type": "image/png", "data": pix.tobytes("png")})
        elif ext in _IMAGE_MIME_TYPES:
            parts.append({"mime_type": _IMAGE_MIME_TYPES[ext], "data": file_path.read_bytes()})
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        return parts

    def _call_model(self, images: list[dict[str, Any]], prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                return self._call_model_once(images, prompt, schema)
            except Exception as exc:  # noqa: BLE001 -- Gemini raises plain Exceptions for API errors
                last_exc = exc
                transient = any(
                    marker in str(exc)
                    for marker in ("RESOURCE_EXHAUSTED", "429", "UNAVAILABLE", "503")
                )
                if not transient:
                    raise
                match = re.search(r"retry in (\d+(?:\.\d+)?)", str(exc), re.IGNORECASE)
                delay = min(float(match.group(1)) + 1 if match else 10 * (attempt + 1), 65)
                time.sleep(delay)
        raise RuntimeError(f"Gemini extraction failed after retries: {last_exc}") from last_exc

    def _call_model_once(self, images: list[dict[str, Any]], prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        from google.genai import types

        client = self._get_client()
        parts = [types.Part.from_bytes(data=img["data"], mime_type=img["mime_type"]) for img in images]
        response = client.models.generate_content(
            model=self.model,
            contents=parts + [prompt],
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=schema,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        return _fix_double_escaped_unicode(json.loads(response.text))

    def _verification_pass(self, images: list[dict[str, Any]], markers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prompt = _VERIFICATION_PROMPT_TEMPLATE.format(
            markers_json=json.dumps(markers, indent=2, ensure_ascii=False)
        )
        data = self._call_model(images, prompt, _VERIFICATION_SCHEMA)
        verified = data.get("markers") or []
        # Verification must never invent markers: only corrections/removals
        # are allowed -- any name not in the original set gets dropped.
        original_names = {m.get("name", "").strip().lower() for m in markers}
        return [m for m in verified if m.get("name", "").strip().lower() in original_names]

    def _finalize(self, markers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate numeric values and deduplicate."""
        seen: set[tuple[str, str]] = set()
        results = []
        for m in markers:
            name = " ".join(str(m.get("name", "")).split()).rstrip(":").strip()
            value = str(m.get("value", "")).strip()
            unit = str(m.get("unit", "")).strip()
            if not name or not _VALUE_RE.fullmatch(value):
                continue
            key = (name.lower(), value)
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "test": name,
                "result": value.replace(",", ""),
                "unit": unit,
                "reference_range": str(m.get("reference_range") or "").strip() or None,
                "interpretation": str(m.get("interpretation") or "").strip() or None,
            })
        return results

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
