"""
Pydantic schemas for uploaded documents and their processing state.

Document metadata: source, upload date, file type, processing status.
Distinguishes the immutable original artifact from its derived structured
representation (observations extracted from it).
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.utils.constants import DocumentStatus


class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    status: DocumentStatus


class DocumentRead(BaseModel):
    id: UUID
    filename: str
    content_type: str
    status: DocumentStatus
    uploaded_at: datetime
    processed_at: datetime | None = None
    error_message: str | None = None
    document_date: str | None = None  # clinical date applied to this document's facts (ISO)
    needs_date: bool = False  # no date was found; a provisional date is in use until the user supplies one

    model_config = {"from_attributes": True}


class DocumentDateUpdate(BaseModel):
    """The clinical date a user supplies for a document where none could be extracted."""

    document_date: date

    @field_validator("document_date")
    @classmethod
    def not_in_the_future(cls, value: date) -> date:
        """A document cannot be issued in the future; this almost always means a typo."""
        if value > date.today():
            raise ValueError("document_date cannot be in the future")
        return value
