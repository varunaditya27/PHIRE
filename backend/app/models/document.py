"""
Pydantic schemas for uploaded documents and their processing state.

Document metadata: source, upload date, file type, processing status.
Distinguishes the immutable original artifact from its derived structured
representation (observations extracted from it).
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.utils.constants import DocumentStatus


class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    status: DocumentStatus
    report_date: date


class DocumentRead(BaseModel):
    id: UUID
    filename: str
    content_type: str
    status: DocumentStatus
    report_date: date
    uploaded_at: datetime
    processed_at: datetime | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}
