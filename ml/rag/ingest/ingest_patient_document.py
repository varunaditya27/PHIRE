"""
Patient document ingestion entry point.

Extracts structured clinical data from a locally-supplied patient document
via LiftExtractor (datalab-to/lift VLM), synthesizes semantically complete
chunks for Chroma + BM25 hybrid retrieval, and maps typed graph facts
(medications, conditions, observations) directly to Neo4j.

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
from pathlib import Path
from typing import Any

from ml.graph.client import GraphClient
from ml.graph.conditions import build_conditions, write_conditions
from ml.graph.document_dates import find_document_date
from ml.graph.medications import build_medications, write_medications
from ml.graph.observations import build_lift_observations, write_observations
from ml.rag.ingest.chunk_synthesizer import synthesize_patient_chunks
from ml.rag.ingest.patient_documents import (
    extract_document_data,
    extract_text,
)
from ml.rag.retriever import Chunk, HybridRetriever

# A patient's own records are the most authoritative possible source for questions about themselves — higher than any public reference material (MedlinePlus 0.9, USDA 0.95, PubMed 0.7 — see run_ingest.py).
PATIENT_DOCUMENT_AUTHORITY = 1.0


def build_chunks(
    file_path: Path,
    extractors: list[Any] | None = None,
    text: str | None = None,
    document_id: str | None = None,
    data: dict[str, Any] | None = None,
    filename: str | None = None,
) -> list[Chunk]:
    """Extract, synthesize, and wrap one patient document as retriever.Chunk objects via Lift.

    `filename` overrides the on-disk name shown as the chunk's source -- the
    backend stores uploads as `<uuid>.<ext>`, which is meaningless to a user.
    """
    if document_id is None:
        document_id = hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]

    if data is None:
        if extractors is not None:
            text = extract_text(file_path, extractors)
        if text is not None:
            if not text.strip():
                raise ValueError(
                    f"No text extracted from {file_path} — empty extraction."
                )
            data = {
                "document_date": None,
                "document_type": "Patient Document",
                "observations": [],
                "medications": [],
                "conditions": [],
                "narrative_sections": [{"heading": "Clinical Document", "content": text}],
            }
        else:
            data = extract_document_data(file_path)

    chunks = synthesize_patient_chunks(
        payload=data,
        document_id=document_id,
        filename=filename or file_path.name,
        authority=PATIENT_DOCUMENT_AUTHORITY,
    )
    if not chunks:
        raise ValueError(
            f"No content extracted from {file_path} — likely empty or unsupported document."
        )
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest one patient document into PHIRE's retriever + graph.")
    parser.add_argument("file_path", type=Path, help="Path to a patient document (PDF or image).")
    parser.add_argument("--no-graph", action="store_true", help="Skip writing structured facts to Neo4j.")
    args = parser.parse_args()

    data = extract_document_data(args.file_path)
    document_id = hashlib.sha256(args.file_path.read_bytes()).hexdigest()[:16]
    raw_date = data.get("document_date")
    effective_date = find_document_date(raw_date) if raw_date else find_document_date(str(data))

    chunks = build_chunks(args.file_path, data=data, document_id=document_id)
    HybridRetriever().add_documents(chunks)
    print(f"Indexed {len(chunks)} chunks from {args.file_path.name} (document_id={document_id})")

    if not args.no_graph:
        medications = build_medications(data["medications"], str(data), document_id, effective_date)
        conditions = build_conditions(data["conditions"], str(data), document_id, effective_date)
        observations = build_lift_observations(data["observations"], document_id, effective_date)

        with GraphClient() as client:
            write_medications(client, document_id, args.file_path.name, medications)
            write_conditions(client, document_id, args.file_path.name, conditions)
            write_observations(client, document_id, args.file_path.name, observations)
        print(f"Wrote {len(medications)} medications, {len(conditions)} conditions, "
              f"{len(observations)} observations to the graph")


if __name__ == "__main__":
    main()
