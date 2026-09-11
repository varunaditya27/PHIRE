"""
POST /api/documents/* — document ingestion endpoints.

Accepts uploaded lab reports / PDFs / scanned images and kicks off ml/'s
ingestion pipeline (see app/services/document_processor.py) in the
background -- OCR/parsing/graph-writing can be slow, so upload returns
immediately with status "uploaded"; poll GET /api/documents/{id} for
"processed"/"failed".
"""

import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile
from sqlalchemy import update
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.database.connection import get_db
from app.database.schemas import Document
from app.models.document import DocumentRead, DocumentUploadResponse
from app.services.document_processor import process_document
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
    report_date: date | None = Form(None),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    validate_upload(file)
    contents = await read_upload_within_limit(file)

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)

    document_id = uuid.uuid4()
    extension = SUPPORTED_FILE_TYPES[file.content_type]
    storage_path = upload_dir / f"{document_id}{extension}"
    effective_report_date = report_date or date.today()

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
            report_date=effective_report_date,
        )
        db.add(document)
        db.commit()
        return document

    document = await run_in_threadpool(_write_and_record)

    background_tasks.add_task(_run_processing, document_id)

    return DocumentUploadResponse(
        id=document.id,
        filename=document.filename,
        status=DocumentStatus.UPLOADED,
        report_date=document.report_date,
    )


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
    background_tasks.add_task(_run_processing, document_id)
    return DocumentUploadResponse(id=document.id, filename=document.filename, status=DocumentStatus.PROCESSING)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db)) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
