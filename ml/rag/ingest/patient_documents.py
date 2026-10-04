"""
Document extraction routing via LiftExtractor.
Replaces previous pypdf and olmOCR split with unified visual extraction.
"""

from pathlib import Path
from typing import Any, Protocol

from ml.rag.ingest.lift_extractor import SUPPORTED_EXTENSIONS, LiftExtractor

_DEFAULT_EXTRACTOR = LiftExtractor()


def supports_document(file_path: Path) -> bool:
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS


def extract_document_data(file_path: Path, extractor: LiftExtractor | None = None) -> dict[str, Any]:
    ext = extractor or _DEFAULT_EXTRACTOR
    return ext.extract(file_path)


class TextExtractor(Protocol):
    """Extracts plain text from one patient-uploaded document file (backward compatibility)."""

    def supports(self, file_path: Path) -> bool: ...
    def extract(self, file_path: Path) -> str: ...


def _format_extracted_data(data: dict[str, Any]) -> str:
    lines = []
    if data.get("document_date"):
        lines.append(f"Date: {data['document_date']}")
    if data.get("document_type"):
        lines.append(f"Document Type: {data['document_type']}")
    for obs in data.get("observations", []):
        unit = f" {obs['unit']}" if obs.get("unit") else ""
        ref = f" (Reference Range: {obs['reference_range']})" if obs.get("reference_range") else ""
        interp = f" -- {obs['interpretation']}" if obs.get("interpretation") else ""
        lines.append(f"{obs.get('name')}: {obs.get('value')}{unit}{ref}{interp}".strip())
    for med in data.get("medications", []):
        dose = f" {med['dosage']}" if med.get("dosage") else ""
        freq = f" {med['frequency']}" if med.get("frequency") else ""
        status = f" ({med['status']})" if med.get("status") else ""
        lines.append(f"Medication: {med.get('name')}{dose}{freq}{status}".strip())
    for cond in data.get("conditions", []):
        status = f" ({cond['status']})" if cond.get("status") else ""
        lines.append(f"Condition: {cond.get('name')}{status}".strip())
    for sec in data.get("narrative_sections", []):
        lines.append(f"[{sec.get('heading', 'Note')}] {sec.get('content', '')}".strip())
    return "\n\n".join(lines).strip()


class PDFTextExtractor:
    """Backward-compatible PDF extractor adapter."""

    def __init__(self, extractor: LiftExtractor | None = None) -> None:
        self._extractor = extractor or _DEFAULT_EXTRACTOR

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".pdf"

    def extract(self, file_path: Path) -> str:
        data = self._extractor.extract(file_path)
        return _format_extracted_data(data)


DEFAULT_EXTRACTORS: list[TextExtractor] = [PDFTextExtractor()]


def extract_text(file_path: Path, extractors: list[TextExtractor] | None = None) -> str:
    """Backward-compatible text extraction routing."""
    if extractors:
        for extractor in extractors:
            if extractor.supports(file_path):
                return extractor.extract(file_path)
        raise ValueError(f"No extractor available for {file_path.suffix!r} files: {file_path}")

    data = extract_document_data(file_path)
    return _format_extracted_data(data)
