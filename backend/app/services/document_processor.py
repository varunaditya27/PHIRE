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
against one uploaded Document row and updates that row's status.

VRAM ordering: all Ollama calls (prose extraction here; OCR already ran
inside extract_text if the upload was an image) happen before this
module touches app.services.ml_singletons.get_retriever() (which loads
the MedCPT embedding model) -- see ingest_patient_document.py's main()
docstring for why concurrent residency OOMs an 8GB GPU. Because
get_retriever() is a shared, process-lifetime singleton (see
ml_singletons.py's module docstring), this ordering only actually holds
on a *fresh* backend process where nothing has called get_retriever()
yet -- once any request (a chat, a search) has loaded the embedding
model once, it stays resident for the rest of the process's life, and a
low-VRAM machine ingesting a document concurrently with that risks the
same OOM ml/'s CLI script was ordered specifically to avoid. Documented
as a known limitation in backend_handoff.md, not solved here.
"""

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.database.schemas import Document
from app.services.ml_singletons import get_retriever, new_graph_client
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

        text = extract_text(path)
        if not text:
            raise ValueError(
                f"No text extracted from {path.name} -- likely a scanned PDF with no embedded "
                "text layer (see ml/rag/ingest/patient_documents.py's PDFTextExtractor docstring)."
            )

        # Reuse the Document row's own id as ml/'s document_id (instead of
        # letting build_chunks re-hash the file) so graph facts and Chroma
        # chunks both key back to the same id this row exposes via the API.
        document_id = str(document.id)
        effective_date = find_document_date(text)

        table_observations = build_table_observations(text, document_id, effective_date)
        facts = extract_facts(text)

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
        document.status = DocumentStatus.FAILED.value
        document.error_message = str(exc)
        db.add(document)
        db.commit()
        raise
