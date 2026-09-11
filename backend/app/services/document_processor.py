"""
Document ingestion pipeline: uploaded file -> ml/'s extraction, chunking,
retrieval indexing, and graph fact writing.

Delegates all actual extraction/parsing to ml.rag.ingest and ml.graph
(mirrors the sequence in ml/rag/ingest/ingest_patient_document.py's
main()) rather than re-implementing document parsing in the backend --
ml/'s pipeline does Lift VLM extraction, synthesized chunking, Option A declarative clinical sentence
citations, and structured graph fact extraction.
This module is orchestration only: it drives ml/'s building blocks
against one uploaded Document row and updates that row's status. On
failure, also rolls back whatever Chroma chunks/Neo4j facts this
document_id's ingestion already wrote (see _rollback_ml_writes) -- a
Document row marked FAILED should mean this document contributed no data
anywhere, not just that its own Postgres row got rolled back.

VRAM ordering: the whole ml/-facing pipeline below (Lift VLM
extraction, then MedCPT embedding via get_retriever()) runs under
app.services.ml_singletons.GPU_LOCK, which also guards router_chat.py's
chat generation -- see that module's docstring for why concurrent GPU
work between ingestion and chat generation can OOM an 8GB GPU.
"""

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.database.schemas import Document
from app.services.ml_singletons import GPU_LOCK, get_lift_extractor, get_retriever, new_graph_client
from app.utils.constants import DocumentStatus


def process_document(db: Session, document: Document) -> None:
    """Run ml/'s ingestion pipeline for one uploaded Document row, in place."""
    document.status = DocumentStatus.PROCESSING.value
    db.add(document)
    db.commit()

    try:
        from ml.graph.conditions import build_conditions, write_conditions
        from ml.graph.medications import build_medications, write_medications
        from ml.graph.observations import build_lift_observations, write_observations
        from ml.rag.ingest.ingest_patient_document import build_chunks
        from ml.rag.ingest.patient_documents import extract_document_data

        path = Path(document.storage_path)
        # The user-selected (or today-defaulted) report_date is the single
        # source of truth for every fact this document contributes to the
        # graph -- not a date guessed from the document's own text -- so the
        # AI always has a concrete, trustworthy reference date per report.
        effective_date = document.report_date.isoformat()

        with GPU_LOCK:
            data = extract_document_data(path, extractor=get_lift_extractor())
            document_id = str(document.id)

            chunks = build_chunks(path, data=data, document_id=document_id)
            get_retriever().add_documents(chunks)

        medications = build_medications(data.get("medications", []), str(data), document_id, effective_date)
        conditions = build_conditions(data.get("conditions", []), str(data), document_id, effective_date)
        observations = build_lift_observations(data.get("observations", []), document_id, effective_date)

        with new_graph_client() as client:
            write_medications(client, document_id, document.filename, medications)
            write_conditions(client, document_id, document.filename, conditions)
            write_observations(client, document_id, document.filename, observations)

        document.status = DocumentStatus.PROCESSED.value
        document.processed_at = datetime.utcnow()
        document.chunk_count = len(chunks)
        db.add(document)
        db.commit()

    except Exception as exc:  # noqa: BLE001 — surfaced on the Document row, not swallowed
        db.rollback()
        _rollback_ml_writes(document.id)
        document.status = DocumentStatus.FAILED.value
        document.error_message = str(exc)
        db.add(document)
        db.commit()
        raise


def _rollback_ml_writes(document_id) -> None:
    """Undo whatever Chroma/Neo4j writes this document_id's ingestion already
    made before it failed -- otherwise a Document row marked FAILED still
    has its chunks/graph facts served by /api/search, /api/evidence/*,
    /api/observations, and /api/timeline (found via review). Both deletes
    are no-ops if nothing was written yet for this document_id (e.g. a
    failure before the Chroma/graph-writing steps ever ran), so it's safe
    to call unconditionally rather than tracking exactly how far the
    pipeline got.
    """
    from ml.graph.deletion import delete_document_facts

    document_id = str(document_id)
    try:
        get_retriever().delete_by_document_id(document_id)
    except Exception as exc:  # noqa: BLE001 -- best-effort; don't mask the original failure
        print(f"document_processor: failed to roll back Chroma chunks for {document_id}: {exc}")
    try:
        with new_graph_client() as client:
            delete_document_facts(client, document_id)
    except Exception as exc:  # noqa: BLE001 -- best-effort; don't mask the original failure
        print(f"document_processor: failed to roll back graph facts for {document_id}: {exc}")
