"""
OllamaVisionExtractor: document extraction for machines without a CUDA GPU.

datalab-to/lift (9.7B) cannot run on a typical laptop CPU (18GB of weights, minutes per page), so the
CPU variant sends each page to a local multimodal model served by Ollama (the same `medgemma:4b` that
answers chat, so there is no extra download) and asks for the same clinical schema lift produces, using
Ollama's schema-constrained output. When a PDF page has a text layer, that text is included as extra
context: it makes digital reports much more reliable than reading the image alone.

Same interface as LiftExtractor (`supports`, `extract`, `gpu_mode`), so everything downstream --
validation, chunk synthesis, graph writes -- is unchanged. Patient data stays on this machine
(`require_localhost`, like every other ml/ Ollama client).
"""

import base64
import io
import os
from pathlib import Path
from typing import Any

import requests

from ml.local_only import require_localhost
from ml.rag.ingest.lift_schema import CLINICAL_DOCUMENT_SCHEMA, validate_lift_payload

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".webp"})
DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_VISION_MODEL") or os.environ.get("OLLAMA_MODEL", "medgemma:4b")
# Per page; a CPU needs minutes for a page the first time the model loads.
DEFAULT_TIMEOUT_SECONDS = float(os.environ.get("OLLAMA_VISION_TIMEOUT_SECONDS", "600"))
MAX_PAGES = 20
RENDER_SCALE = 2.0  # ~144 dpi: sharp enough for small lab-table text, small enough to keep the image cheap
MAX_IMAGE_SIDE = 1600

PROMPT = """You are reading one page of a patient's medical document. Extract the clinical data you can see into the \
JSON schema. Rules: copy values and units exactly as printed; do not guess or infer anything that is not on the page; \
omit a field you cannot read rather than inventing it; a blood pressure is one observation named "Blood Pressure" with \
a value like "148/92"; the document_date is the date the report/test/visit happened (not a date of birth).
{text_block}"""


def _page_images(path: Path) -> list[tuple[bytes, str]]:
    """(PNG bytes, text layer) per page: PDFs are rendered with pypdfium2, images are used as-is."""
    from PIL import Image

    def png(image: "Image.Image") -> bytes:
        image = image.convert("RGB")
        image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    if path.suffix.lower() != ".pdf":
        with Image.open(path) as image:
            return [(png(image), "")]

    import pypdfium2

    pdf = pypdfium2.PdfDocument(str(path))
    try:
        pages = []
        for index in range(min(len(pdf), MAX_PAGES)):
            page = pdf[index]
            text = page.get_textpage().get_text_range().strip()
            pages.append((png(page.render(scale=RENDER_SCALE).to_pil()), text))
        return pages
    finally:
        pdf.close()


def merge_pages(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine per-page payloads: first non-empty date/type, every distinct observation/medication/condition."""
    merged: dict[str, Any] = {"document_date": None, "document_type": None, "observations": [], "medications": [],
                              "conditions": [], "narrative_sections": []}
    seen: set[tuple] = set()
    for payload in payloads:
        merged["document_date"] = merged["document_date"] or payload.get("document_date")
        merged["document_type"] = merged["document_type"] or payload.get("document_type")
        for key, identity in (("observations", ("name", "value", "unit")), ("medications", ("name", "dosage", "frequency")),
                              ("conditions", ("name",))):
            for item in payload.get(key, []):
                marker = (key, *(str(item.get(f, "")).strip().lower() for f in identity))
                if marker not in seen:
                    seen.add(marker)
                    merged[key].append(item)
        merged["narrative_sections"] += payload.get("narrative_sections", [])
    return merged


class OllamaVisionExtractor:
    """Extracts structured clinical data from PDFs and images with a local Ollama vision model."""

    # The model is served by Ollama, so the chat group stays resident while extracting.
    gpu_mode = "chat"

    def __init__(self, model: str | None = None, host: str | None = None, timeout: float | None = None, post=requests.post) -> None:
        self.model = model or DEFAULT_MODEL
        self.host = host or DEFAULT_HOST
        self.timeout = timeout or DEFAULT_TIMEOUT_SECONDS
        self._post = post  # injectable so tests need no running Ollama
        require_localhost(self.host)

    def supports(self, file_path: Path) -> bool:
        """Whether this extractor handles the file's extension."""
        return file_path.suffix.lower() in SUPPORTED_EXTENSIONS

    def extract(self, file_path: Path) -> dict[str, Any]:
        """Structured clinical JSON for a PDF or image, one model call per page, merged and validated."""
        if not self.supports(file_path):
            raise ValueError(f"Unsupported file format {file_path.suffix} for extraction.")
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        pages = _page_images(file_path)
        try:
            return validate_lift_payload(merge_pages([self._extract_page(image, text) for image, text in pages]))
        except requests.RequestException as exc:
            raise RuntimeError(f"Vision extraction via Ollama ({self.model}) failed for {file_path}: {exc}") from exc

    def _extract_page(self, image: bytes, text: str) -> dict[str, Any]:
        """One page -> schema-constrained JSON from the model."""
        text_block = f"\nThe page's own text layer (may be incomplete or out of order) is:\n---\n{text[:6000]}\n---" if text else ""
        response = self._post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "format": CLINICAL_DOCUMENT_SCHEMA,
                "options": {"temperature": 0, "num_ctx": 8192},
                "messages": [{"role": "user", "content": PROMPT.format(text_block=text_block),
                              "images": [base64.b64encode(image).decode("ascii")]}],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        import json

        try:
            return json.loads(response.json()["message"]["content"])
        except (json.JSONDecodeError, KeyError):
            return {}  # an unreadable page contributes nothing rather than failing the whole document
