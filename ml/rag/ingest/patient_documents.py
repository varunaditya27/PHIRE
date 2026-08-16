"""
Text extraction from patient-uploaded documents.

Pluggable by design: PDFTextExtractor handles text-based PDFs;
OCRTextExtractor (ml/rag/ingest/ocr.py) handles scanned/photographed
images via olmOCR-v2 run locally through Ollama — model choice
benchmarked in experiments/RESULTS.md, not assumed. Adding another format
later means adding another TextExtractor to DEFAULT_EXTRACTORS, without
touching the ingestion pipeline around it (ingest_patient_document.py only
calls extract_text, never a concrete extractor class directly).
"""

from pathlib import Path
from typing import Protocol

import pypdf

from ml.rag.ingest.ocr import OCRTextExtractor


class TextExtractor(Protocol):
    """Extracts plain text from one patient-uploaded document file."""

    def supports(self, file_path: Path) -> bool: ...
    def extract(self, file_path: Path) -> str: ...


class PDFTextExtractor:
    """Extracts embedded text from text-based PDFs via pypdf.

    Does not perform OCR — a scanned/photographed PDF (embedded images,
    no text layer) extracts as empty or near-empty text. extract_text()
    routes purely on file extension, matching this extractor first for
    any .pdf regardless of content, so a scanned PDF does NOT fall
    through to OCRTextExtractor (which only supports raw image formats —
    see its SUPPORTED_SUFFIXES) — that combination is a known gap, not
    yet handled by either extractor. Surfaced explicitly by returning ""
    rather than silently indexing garbage — see
    ingest_patient_document.py's handling of an empty extraction result.
    """

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".pdf"

    def extract(self, file_path: Path) -> str:
        reader = pypdf.PdfReader(str(file_path))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()


DEFAULT_EXTRACTORS: list[TextExtractor] = [PDFTextExtractor(), OCRTextExtractor()]


def extract_text(file_path: Path, extractors: list[TextExtractor] | None = None) -> str:
    """Route file_path to the first extractor that supports its format."""
    for extractor in extractors or DEFAULT_EXTRACTORS:
        if extractor.supports(file_path):
            return extractor.extract(file_path)
    raise ValueError(f"No extractor available for {file_path.suffix!r} files: {file_path}")
