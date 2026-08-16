"""
Patient document ingestion entry point.

Extracts text from a locally-supplied patient document (lab report,
health record), chunks it, and indexes it into the same Chroma + BM25
store retriever.py searches (same mechanism as run_ingest.py's public
reference evidence, but for one patient's own documents), and extracts
typed graph facts two ways: deterministically for tabular data (labs,
vitals — the table's own headers are the schema, no LLM needed) and via
schema-constrained LLM extraction for free-text sections (medications,
conditions, observations mentioned in prose — see
ml/graph/prose_extraction.py and ml/graph/experiments/RESULTS.md for the
method/model choice).

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
from ml.graph.conditions import build_conditions, write_conditions
from ml.graph.medications import build_medications, write_medications
from ml.graph.observations import build_prose_observations, build_table_observations, find_document_date, write_observations
from ml.graph.prose_extraction import extract_facts
from ml.rag.ingest.chunking import chunk_ocr_text, locate_chunk_offsets
from ml.rag.ingest.patient_documents import TextExtractor, extract_text
from ml.rag.retriever import Chunk, HybridRetriever

# A patient's own records are the most authoritative possible source for questions about themselves — higher than any public reference material (MedlinePlus 0.9, USDA 0.95, PubMed 0.7 — see run_ingest.py).
PATIENT_DOCUMENT_AUTHORITY = 1.0


def build_chunks(
    file_path: Path, extractors: list[TextExtractor] | None = None, text: str | None = None,
    document_id: str | None = None,
) -> list[Chunk]:
    """Extract, chunk, and wrap one patient document as retriever.Chunk objects.

    Pass text to skip re-extraction if the caller already has it (main()
    also needs the raw text for graph/Observation extraction, and OCR
    extraction is a real model call — not something to pay for twice).
    Pass document_id likewise to skip re-hashing the file — main() also
    needs it before calling this, to key the graph writes.
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
    if document_id is None:
        document_id = hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]
    # ingested_date, not published_date: this is when PHIRE indexed the file, not the report's clinical date (not reliably parseable from free text yet) — reranker.py's recency scoring only readspublished_date, so this deliberately doesn't feed that signal.
    ingested_date = datetime.now(timezone.utc).date().isoformat()

    pieces = chunk_ocr_text(text)
    # None for table-row chunks (reformatted, not verbatim in text — see
    # locate_chunk_offsets' docstring), a real span for everything else.
    offsets = locate_chunk_offsets(text, pieces)

    chunks = []
    for i, (piece, span) in enumerate(zip(pieces, offsets)):
        metadata = {
            "source": "patient_document",
            "document_id": document_id,
            "filename": file_path.name,
            "ingested_date": ingested_date,
            "authority": PATIENT_DOCUMENT_AUTHORITY,
        }
        if span is not None:
            metadata["char_start"], metadata["char_end"] = span
        chunks.append(Chunk(id=f"patient_doc_{document_id}_{i}", text=piece, metadata=metadata))
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest one patient document into PHIRE's retriever + graph.")
    parser.add_argument("file_path", type=Path, help="Path to a patient document (text-based PDF, or JPG/PNG for OCR).")
    parser.add_argument("--no-graph", action="store_true", help="Skip writing structured facts to Neo4j.")
    args = parser.parse_args()

    text = extract_text(args.file_path)
    if not text:
        raise ValueError(f"No text extracted from {args.file_path} (see build_chunks' docstring for why this can happen)")
    document_id = hashlib.sha256(args.file_path.read_bytes()).hexdigest()[:16]
    # Scanned once here and threaded through every build_* call below —
    # they'd otherwise each independently regex-scan the same document_text.
    effective_date = find_document_date(text)

    # All Ollama calls (OCR above, prose extraction here) happen before
    # HybridRetriever loads MedCPT below — both release VRAM immediately
    # after their own call (keep_alive: 0), but running them before the
    # embedding model loads avoids any window where both are resident on
    # this 8GB GPU at once (verified live: this ordering was needed to
    # avoid an OOM crash).
    table_observations = build_table_observations(text, document_id, effective_date)
    facts = {"medications": [], "conditions": [], "observations": []}
    if not args.no_graph:
        facts = extract_facts(text)

    chunks = build_chunks(args.file_path, text=text, document_id=document_id)
    HybridRetriever().add_documents(chunks)
    print(f"Indexed {len(chunks)} chunks from {args.file_path.name} (document_id={document_id})")

    if not args.no_graph:
        medications = build_medications(facts["medications"], text, document_id, effective_date)
        conditions = build_conditions(facts["conditions"], text, document_id, effective_date)
        # Deduplicated by id, table entries winning ties: prose extraction
        # runs on the whole document text, which includes the raw table
        # content, so it can re-extract the same lab values table
        # extraction already found deterministically. Neo4j's MERGE
        # would collapse the duplicates either way, but counting the
        # pre-dedup list here would print a misleading "wrote N" total
        # that doesn't match the actual distinct facts (verified live:
        # a single 8-row lab table reported "16 observations").
        prose_observations = build_prose_observations(facts["observations"], text, document_id, effective_date)
        observations_by_id = {obs["id"]: obs for obs in prose_observations}
        observations_by_id.update({obs["id"]: obs for obs in table_observations})
        observations = list(observations_by_id.values())
        with GraphClient() as client:
            write_medications(client, document_id, args.file_path.name, medications)
            write_conditions(client, document_id, args.file_path.name, conditions)
            write_observations(client, document_id, args.file_path.name, observations)
        print(f"Wrote {len(medications)} medications, {len(conditions)} conditions, "
              f"{len(observations)} observations to the graph")


if __name__ == "__main__":
    main()
