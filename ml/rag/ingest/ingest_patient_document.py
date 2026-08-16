"""
Patient document ingestion entry point.

Extracts text from a locally-supplied patient document (lab report,
health record), chunks it, and indexes it into the same Chroma + BM25
store retriever.py searches (same mechanism as run_ingest.py's public
reference evidence, but for one patient's own documents), and — for any
tabular data the document contains (labs, vitals) — parses it into typed
Observation nodes written to the Neo4j graph (ml/graph/). Table data has
an explicit schema (its own column headers), so this needs no LLM
extraction; free-text sections (progress notes, radiology impressions)
aren't graph-extracted yet — that's a harder, separate problem.

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

from ml.graph.client import GraphClient
from ml.graph.observations import extract_observations, write_observations
from ml.rag.ingest.chunking import chunk_ocr_text
from ml.rag.ingest.patient_documents import TextExtractor, extract_text
from ml.rag.retriever import Chunk, HybridRetriever

# A patient's own records are the most authoritative possible source for questions about themselves — higher than any public reference material (MedlinePlus 0.9, USDA 0.95, PubMed 0.7 — see run_ingest.py).
PATIENT_DOCUMENT_AUTHORITY = 1.0


def build_chunks(
    file_path: Path, extractors: list[TextExtractor] | None = None, text: str | None = None,
) -> list[Chunk]:
    """Extract, chunk, and wrap one patient document as retriever.Chunk objects.

    Pass text to skip re-extraction if the caller already has it (main()
    also needs the raw text for graph/Observation extraction, and OCR
    extraction is a real model call — not something to pay for twice).
    """
    if text is None:
        text = extract_text(file_path, extractors)
    if not text:
        raise ValueError(
            f"No text extracted from {file_path} — likely a scanned PDF with no "
            "embedded text layer (a photo/image file would route to OCRTextExtractor; "
            "a scanned PDF specifically isn't handled by either extractor, see "
            "patient_documents.py's PDFTextExtractor docstring)"
        )
    document_id = hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]
    # ingested_date, not published_date: this is when PHIRE indexed the file, not the report's clinical date (not reliably parseable from free text yet) — reranker.py's recency scoring only readspublished_date, so this deliberately doesn't feed that signal.
    ingested_date = datetime.now(timezone.utc).date().isoformat()

    chunks = []
    for i, piece in enumerate(chunk_ocr_text(text)):
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
    parser = argparse.ArgumentParser(description="Ingest one patient document into PHIRE's retriever + graph.")
    parser.add_argument("file_path", type=Path, help="Path to a patient document (text-based PDF, or JPG/PNG for OCR).")
    parser.add_argument("--no-graph", action="store_true", help="Skip writing structured Observations to Neo4j.")
    args = parser.parse_args()

    text = extract_text(args.file_path)
    if not text:
        raise ValueError(f"No text extracted from {args.file_path} (see build_chunks' docstring for why this can happen)")

    chunks = build_chunks(args.file_path, text=text)
    HybridRetriever().add_documents(chunks)
    document_id = chunks[0].metadata["document_id"]
    print(f"Indexed {len(chunks)} chunks from {args.file_path.name} (document_id={document_id})")

    if not args.no_graph:
        observations = extract_observations(text, document_id)
        if observations:
            with GraphClient() as client:
                write_observations(client, document_id, args.file_path.name, observations)
            print(f"Wrote {len(observations)} observations to the graph")


if __name__ == "__main__":
    main()
