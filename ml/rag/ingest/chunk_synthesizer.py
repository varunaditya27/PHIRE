"""
Option A RAG Chunk Synthesizer.

Converts structured Lift extraction outputs into clean, semantically
complete clinical sentences for indexing into Chroma and BM25.
Maximizes NLI (BART-large-MNLI) entailment scoring accuracy.
"""

from datetime import datetime, timezone
from typing import Any

from ml.rag.ingest.lift_schema import validate_lift_payload
from ml.rag.retriever import Chunk

DEFAULT_PATIENT_AUTHORITY = 1.0


def synthesize_patient_chunks(
    payload: dict[str, Any],
    document_id: str,
    filename: str,
    authority: float = DEFAULT_PATIENT_AUTHORITY,
) -> list[Chunk]:
    """Convert validated Lift structured payload into retriever Chunk objects."""
    data = validate_lift_payload(payload)
    doc_date = data.get("document_date") or "Unspecified Date"
    doc_type = data.get("document_type") or "Medical Document"
    ingested_date = datetime.now(timezone.utc).date().isoformat()

    chunks: list[Chunk] = []
    chunk_index = 0

    base_metadata = {
        "source": "patient_document",
        "document_id": document_id,
        "filename": filename,
        "document_type": doc_type,
        "document_date": doc_date,
        "ingested_date": ingested_date,
        "authority": authority,
    }

    # 1. Synthesize Observation Chunks
    for obs in data["observations"]:
        name = obs["name"]
        val = obs["value"]
        unit = f" {obs['unit']}" if obs.get("unit") else ""
        ref = f" (Reference Range: {obs['reference_range']})" if obs.get("reference_range") else ""
        interp = f", Interpretation: {obs['interpretation']}" if obs.get("interpretation") else ""

        text = f"On {doc_date}, {name} was {val}{unit}{ref}{interp}. Source: {filename}."
        meta = dict(base_metadata)
        meta["entity_type"] = "observation"
        meta["entity_name"] = name
        chunks.append(Chunk(id=f"patient_doc_{document_id}_{chunk_index}", text=text, metadata=meta))
        chunk_index += 1

    # 2. Synthesize Medication Chunks
    for med in data["medications"]:
        name = med["name"]
        dosage = med.get("dosage") or "unspecified dose"
        freq = med.get("frequency") or "unspecified frequency"
        status = med.get("status") or "unspecified status"

        text = f"{name} ({dosage}, {freq}) - Status: {status}. Documented in {filename} on {doc_date}."
        meta = dict(base_metadata)
        meta["entity_type"] = "medication"
        meta["entity_name"] = name
        chunks.append(Chunk(id=f"patient_doc_{document_id}_{chunk_index}", text=text, metadata=meta))
        chunk_index += 1

    # 3. Synthesize Condition Chunks
    for cond in data["conditions"]:
        name = cond["name"]
        status = cond.get("status") or "unspecified"

        text = f"Condition: {name} (Status: {status}). Documented in {filename} on {doc_date}."
        meta = dict(base_metadata)
        meta["entity_type"] = "condition"
        meta["entity_name"] = name
        chunks.append(Chunk(id=f"patient_doc_{document_id}_{chunk_index}", text=text, metadata=meta))
        chunk_index += 1

    # 4. Synthesize Narrative Section Chunks
    for sec in data["narrative_sections"]:
        heading = sec.get("heading") or "Clinical Note"
        content = sec.get("content") or ""
        if not content.strip():
            continue

        text = f"[{heading}] {content} (Source: {filename}, Date: {doc_date})"
        meta = dict(base_metadata)
        meta["entity_type"] = "narrative"
        meta["heading"] = heading
        chunks.append(Chunk(id=f"patient_doc_{document_id}_{chunk_index}", text=text, metadata=meta))
        chunk_index += 1

    return chunks
