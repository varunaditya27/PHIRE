"""
Text extraction from patient-uploaded documents.

Pluggable by design: PDFTextExtractor handles v1 scope (text-based PDFs).
An OCR-based extractor for scanned/photographed documents — people
uploading a phone photo of a hard-copy report rather than an actual PDF is
a real, expected case — is the next TextExtractor implementation to add,
without touching the ingestion pipeline around it (ingest_patient_document.py
only calls extract_text, never a concrete extractor class directly). Model
choice is already benchmarked and decided: olmOCR-v2 (2-7B-1025) at
Q4_K_M, run locally via Ollama — see experiments/RESULTS.md. Not yet wired
in as an actual extractor class here.
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

    Does not perform OCR — a scanned/photographed PDF with no embedded
    text layer extracts as empty or near-empty text. That's a real
    limitation, surfaced explicitly by returning "" rather than silently
    indexing garbage — see ingest_patient_document.py's handling of an
    empty extraction result. An OCR extractor (olmOCR-v2, per
    experiments/RESULTS.md) is the planned fix, not yet implemented.
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
