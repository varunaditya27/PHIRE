"""
Text extraction from patient-uploaded documents.

Pluggable by design: PDFTextExtractor handles today's v1 scope (text-based PDFs). An OCR-based extractor for scanned/photographed documents — people uploading a phone photo of a hard-copy report rather than an actual PDF is a real, expected case — can be added later as another TextExtractor implementation without touching the ingestion pipeline around it (ingest_patient_document.py only calls extract_text, never a concrete extractor class directly).
"""

from pathlib import Path
from typing import Protocol

import pypdf


class TextExtractor(Protocol):
    """Extracts plain text from one patient-uploaded document file."""

    def supports(self, file_path: Path) -> bool: ...
    def extract(self, file_path: Path) -> str: ...


class PDFTextExtractor:
    """Extracts embedded text from text-based PDFs via pypdf.

    Does not perform OCR — a scanned/photographed PDF with no embedded text layer extracts as empty or near-empty text. That's a real v1 limitation (OCR tooling is scoped for Month 2-6 per docs/OPEN_SOURCE_TOOLS.md, not MVP), surfaced explicitly by returning "" rather than silently indexing garbage — see ingest_patient_document.py's handling of an empty extraction result.
    """

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".pdf"

    def extract(self, file_path: Path) -> str:
        reader = pypdf.PdfReader(str(file_path))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()


DEFAULT_EXTRACTORS: list[TextExtractor] = [PDFTextExtractor()]


def extract_text(file_path: Path, extractors: list[TextExtractor] | None = None) -> str:
    """Route file_path to the first extractor that supports its format."""
    for extractor in extractors or DEFAULT_EXTRACTORS:
        if extractor.supports(file_path):
            return extractor.extract(file_path)
    raise ValueError(f"No extractor available for {file_path.suffix!r} files: {file_path}")
