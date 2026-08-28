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

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

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
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    validate_upload(file)
    contents = await read_upload_within_limit(file)

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    document_id = uuid.uuid4()
    extension = SUPPORTED_FILE_TYPES[file.content_type]
    storage_path = upload_dir / f"{document_id}{extension}"
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

    background_tasks.add_task(_run_processing, document_id)

    return DocumentUploadResponse(id=document.id, filename=document.filename, status=DocumentStatus.UPLOADED)


@router.post("/{document_id}/process", response_model=DocumentUploadResponse)
def reprocess_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status == DocumentStatus.PROCESSING.value:
        raise HTTPException(status_code=409, detail="Document is already being processed.")

    # Flip status here, synchronously, rather than leaving it to
    # process_document()'s own PROCESSING write -- that write doesn't
    # happen until the background task actually runs, so two rapid calls
    # would both pass the check above and both get scheduled.
    document.status = DocumentStatus.PROCESSING.value
    db.commit()

    background_tasks.add_task(_run_processing, document_id)
    return DocumentUploadResponse(id=document.id, filename=document.filename, status=DocumentStatus.PROCESSING)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db)) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
