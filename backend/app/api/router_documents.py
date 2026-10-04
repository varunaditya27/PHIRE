"""
POST /api/documents/* — document ingestion endpoints.

Accepts uploaded lab reports / PDFs / scanned images and kicks off ml/'s
ingestion pipeline (see app/services/document_processor.py) in the
background -- OCR/parsing/graph-writing can be slow, so upload returns
immediately with status "uploaded"; poll GET /api/documents/{id} for
"processed"/"failed".
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, UploadFile
from sqlalchemy import update
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.database.connection import get_db
from app.database.schemas import Document
from app.models.document import DocumentDateUpdate, DocumentRead, DocumentUploadResponse
from app.services import progress
from app.services.gpu_modes import CHAT, gpu_mode
from app.services.ml_singletons import get_retriever, new_graph_client
from app.services.document_processor import process_document, redate_document
from app.utils.constants import SUPPORTED_FILE_TYPES, DocumentStatus
from app.utils.validators import read_upload_within_limit, validate_upload

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _run_processing(document_id: uuid.UUID) -> None:
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is not None:
            process_document(db, document)
    finally:
        db.close()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    validate_upload(file)
    contents = await read_upload_within_limit(file)

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)

    document_id = uuid.uuid4()
    extension = SUPPORTED_FILE_TYPES[file.content_type]
    storage_path = upload_dir / f"{document_id}{extension}"

    def _write_and_record() -> Document:
        # mkdir/write_bytes/commit are all blocking calls -- run off the
        # event loop (this handler is async def for read_upload_within_limit's
        # await above) so a large upload doesn't stall every other
        # concurrent request this worker is serving.
        upload_dir.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(contents)
        document = Document(
            id=document_id,
            filename=file.filename or storage_path.name,
            content_type=file.content_type,
            storage_path=str(storage_path),
            status=DocumentStatus.UPLOADED.value,
        )
        db.add(document)
        db.commit()
        return document

    document = await run_in_threadpool(_write_and_record)

    progress.reset(str(document_id))
    progress.publish(str(document_id), "queued", "Upload received, waiting to start")
    background_tasks.add_task(_run_processing, document_id)

    return DocumentUploadResponse(id=document.id, filename=document.filename, status=DocumentStatus.UPLOADED)


@router.post("/{document_id}/process", response_model=DocumentUploadResponse)
def reprocess_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    # A read-then-write check (SELECT status, then UPDATE if not
    # PROCESSING) isn't atomic across two concurrent requests -- each has
    # its own DB session/transaction, so both can read the pre-update
    # status before either commits (found via review). A single
    # conditional UPDATE is: Postgres row-locks the row for the first
    # transaction's UPDATE, so a second concurrent UPDATE targeting the
    # same id blocks until the first commits, then re-evaluates the WHERE
    # clause against the now-PROCESSING row and matches zero rows.
    result = db.execute(
        update(Document)
        .where(Document.id == document_id, Document.status != DocumentStatus.PROCESSING.value)
        .values(status=DocumentStatus.PROCESSING.value)
    )
    db.commit()

    if result.rowcount == 0:
        document = db.get(Document, document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        raise HTTPException(status_code=409, detail="Document is already being processed.")

    document = db.get(Document, document_id)
    progress.reset(str(document_id))
    progress.publish(str(document_id), "queued", "Reprocessing, waiting to start")
    background_tasks.add_task(_run_processing, document_id)
    return DocumentUploadResponse(id=document.id, filename=document.filename, status=DocumentStatus.PROCESSING)


@router.get("", response_model=list[DocumentRead])
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    """All uploaded documents, newest first -- the source of truth for the documents page."""
    return db.query(Document).order_by(Document.uploaded_at.desc()).all()


@router.put("/{document_id}/date", response_model=DocumentRead)
def set_document_date(document_id: uuid.UUID, body: DocumentDateUpdate, db: Session = Depends(get_db)) -> Document:
    """Supply (or correct) a document's clinical date; its facts and search chunks are rebuilt at that date.

    For a document flagged `needs_date` because no date could be extracted. Uses the saved extraction, so
    it takes seconds, not a re-run of the vision model.
    """
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status != DocumentStatus.PROCESSED.value:
        raise HTTPException(status_code=409, detail="Document is not processed yet; set its date once it finishes.")
    if document.extracted_data is None:
        raise HTTPException(
            status_code=409,
            detail="This document was processed before extractions were saved; delete it and upload it again.",
        )
    redate_document(db, document, body.document_date.isoformat())
    return document


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db)) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    """Remove a document everywhere it was written: Chroma chunks, Neo4j facts,
    the stored file, and its Postgres row.

    Refused with 409 while it is still processing -- the background worker
    would otherwise write chunks/facts for a document that no longer exists.
    """
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status == DocumentStatus.PROCESSING.value:
        raise HTTPException(status_code=409, detail="Document is still processing; try again when it finishes.")

    # Errors propagate (500, row kept) instead of being swallowed like the
    # best-effort rollback after a failed ingestion: a "deleted" document
    # whose facts still answer chat would be a silent privacy failure, and
    # keeping the row lets the user retry. The retriever needs the CHAT-group
    # GPU models, hence gpu_mode.
    from ml.graph.deletion import delete_document_facts

    with gpu_mode(CHAT):
        get_retriever().delete_by_document_id(str(document.id))
    with new_graph_client() as client:
        delete_document_facts(client, str(document.id))
    Path(document.storage_path).unlink(missing_ok=True)
    db.delete(document)
    db.commit()
    progress.forget(str(document_id))
    return Response(status_code=204)
