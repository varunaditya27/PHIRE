"""
Patient document ingestion entry point.

Extracts text from a locally-supplied patient document (lab report,
health record), chunks it, and indexes it into the same Chroma + BM25
store retriever.py searches — same mechanism as run_ingest.py's public
reference evidence, but for one patient's own documents.

PHIRE runs as one local instance per person (see CLAUDE.md's "all patient
data stays local" principle) — there is no multi-patient isolation here
by design, not by oversight. If PHIRE is ever deployed multi-tenant, this
needs a patient_id metadata filter added to both this module and
retriever.py's query path before it's safe to reuse as-is.

Standalone by design: this only touches local files and the existing
retriever — no dependency on the backend's upload endpoint. Anika's
/api/documents/upload can call build_chunks() directly (or shell out to
this script) once it exists; nothing here needs to change for that.

Run from the repo root:

    ml/.venv/bin/python -m ml.rag.ingest.ingest_patient_document /path/to/report.pdf
"""

import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from ml.rag.ingest.chunking import chunk_lines
from ml.rag.ingest.patient_documents import TextExtractor, extract_text
from ml.rag.retriever import Chunk, HybridRetriever

# A patient's own records are the most authoritative possible source for questions about themselves — higher than any public reference material (MedlinePlus 0.9, USDA 0.95, PubMed 0.7 — see run_ingest.py).
PATIENT_DOCUMENT_AUTHORITY = 1.0


def build_chunks(file_path: Path, extractors: list[TextExtractor] | None = None) -> list[Chunk]:
    """Extract, chunk, and wrap one patient document as retriever.Chunk objects."""
    text = extract_text(file_path, extractors)
    if not text:
        raise ValueError(
            f"No text extracted from {file_path} — likely a scanned/image-only PDF "
            "(OCR not yet supported, see patient_documents.py)"
        )
    document_id = hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]
    # ingested_date, not published_date: this is when PHIRE indexed the file, not the report's clinical date (not reliably parseable from free text yet) — reranker.py's recency scoring only readspublished_date, so this deliberately doesn't feed that signal.
    ingested_date = datetime.now(timezone.utc).date().isoformat()

    chunks = []
    for i, piece in enumerate(chunk_lines(text)):
        chunks.append(Chunk(
            id=f"patient_doc_{document_id}_{i}",
            text=piece,
            metadata={
                "source": "patient_document",
                "document_id": document_id,
                "filename": file_path.name,
                "ingested_date": ingested_date,
                "authority": PATIENT_DOCUMENT_AUTHORITY,
            },
        ))
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest one patient document into PHIRE's retriever.")
    parser.add_argument("file_path", type=Path, help="Path to a patient document (text-based PDF).")
    args = parser.parse_args()

    chunks = build_chunks(args.file_path)
    HybridRetriever().add_documents(chunks)
    print(f"Indexed {len(chunks)} chunks from {args.file_path.name} (document_id={chunks[0].metadata['document_id']})")


if __name__ == "__main__":
    main()
