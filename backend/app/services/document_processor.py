"""
Document ingestion pipeline: uploaded file -> ml/'s extraction, chunking,
retrieval indexing, and graph fact writing.

Delegates all actual extraction/parsing to ml.rag.ingest and ml.graph
(mirrors the sequence in ml/rag/ingest/ingest_patient_document.py's
main()) rather than re-implementing document parsing in the backend --
ml/'s pipeline does OCR routing, table-aware chunking, exact char-span
citations, and structured graph fact extraction; backend's prior
standalone parser (PyMuPDF + a regex lab-line matcher) did none of that.
This module is orchestration only: it drives ml/'s building blocks
against one uploaded Document row and updates that row's status. On
failure, also rolls back whatever Chroma chunks/Neo4j facts this
document_id's ingestion already wrote (see _rollback_ml_writes) -- a
Document row marked FAILED should mean this document contributed no data
anywhere, not just that its own Postgres row got rolled back.

VRAM ordering: the whole ml/-facing pipeline below (Ollama OCR/prose
extraction, then MedCPT embedding via get_retriever()) runs under
app.services.ml_singletons.GPU_LOCK, which also guards router_chat.py's
chat generation -- see that module's docstring for why concurrent GPU
work between ingestion and chat generation can OOM an 8GB GPU.
"""

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.schemas import Document
from app.services.ml_singletons import GPU_LOCK, get_retriever, new_graph_client
from app.utils.constants import DocumentStatus


def process_document(db: Session, document: Document) -> None:
    """Run ml/'s ingestion pipeline for one uploaded Document row, in place."""
    document.status = DocumentStatus.PROCESSING.value
    db.add(document)
    db.commit()

    try:
        from ml.graph.conditions import build_conditions, write_conditions
        from ml.graph.document_dates import find_document_date
        from ml.graph.medications import build_medications, write_medications
        from ml.graph.observations import build_prose_observations, build_table_observations, write_observations
        from ml.graph.prose_extraction import extract_facts
        from ml.rag.ingest.ingest_patient_document import build_chunks
        from ml.rag.ingest.patient_documents import extract_text

        path = Path(document.storage_path)

        # GPU_LOCK held for this whole span, not just the embedding call --
        # extract_text (OCR, scanned docs) and extract_facts (prose
        # extraction) are Ollama calls too, and get_retriever() loads/uses
        # the MedCPT embedding model (see this module's + ml_singletons.py's
        # docstrings).
        with GPU_LOCK:
            text = extract_text(path)
            if not text:
                raise ValueError(
                    f"No text extracted from {path.name} -- likely a scanned PDF with no embedded "
                    "text layer (see ml/rag/ingest/patient_documents.py's PDFTextExtractor docstring)."
                )

            # Reuse the Document row's own id as ml/'s document_id (instead
            # of letting build_chunks re-hash the file) so graph facts and
            # Chroma chunks both key back to the same id this row exposes
            # via the API.
            document_id = str(document.id)
            effective_date = find_document_date(text)

            table_observations = build_table_observations(text, document_id, effective_date)
            # Threaded through explicitly rather than relying on
            # extract_facts()'s own default -- backend/.env's
            # PROSE_EXTRACTION_MODEL was previously silently ignored here
            # (found via review), same reasoning as ml_singletons.py's
            # "constructor args passed explicitly from Settings" note.
            facts = extract_facts(text, model=get_settings().prose_extraction_model)

            chunks = build_chunks(path, text=text, document_id=document_id)
            get_retriever().add_documents(chunks)

        medications = build_medications(facts["medications"], text, document_id, effective_date)
        conditions = build_conditions(facts["conditions"], text, document_id, effective_date)
        prose_observations = build_prose_observations(facts["observations"], text, document_id, effective_date)
        # Table entries win ties on duplicate ids -- table extraction is
        # deterministic (the table's own headers are the schema), prose
        # extraction on the same document text can re-find the same lab
        # values via the LLM (see ingest_patient_document.py's main()).
        observations_by_id = {obs["id"]: obs for obs in prose_observations}
        observations_by_id.update({obs["id"]: obs for obs in table_observations})
        observations = list(observations_by_id.values())

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
