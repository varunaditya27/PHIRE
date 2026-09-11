"""
SQLAlchemy ORM models (tables) backing the Pydantic schemas in app/models/.

Postgres holds only what ml/ doesn't own: upload bookkeeping (documents),
chat history, a claims audit trail, and the HIPAA access log.
Observations/medications/conditions ("patient facts") and evidence chunks
live in ml/'s own stores instead -- Neo4j (ml/graph, see
app/services/graph_reader.py) and Chroma (ml/rag/retriever.py, see
app/services/ml_singletons.py) -- rather than being duplicated here. An
earlier version of this schema had its own observations/evidence_passages
tables populated by a parallel, weaker backend-side extractor; retired in
favor of reading ml/'s richer, already-ingested data directly.

No patient_id column anywhere: PHIRE runs as one local instance per
person (ml/rag/ingest/ingest_patient_document.py's docstring, CLAUDE.md's
"all patient data stays local" principle) -- ml/graph hardcodes a single
Neo4j Patient{id: "self"} node and nothing in ml/ takes a patient_id
parameter. These tables mirror that: single implicit patient, no
per-row scoping needed.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base
from app.utils.constants import DocumentStatus, EvidenceStatus


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Document(Base):
    """Upload bookkeeping only -- text/graph extraction is ml/'s job (see
    app/services/document_processor.py), so this row just tracks the
    immutable original artifact and its processing status, not derived
    structured data."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)  # immutable original artifact
    status: Mapped[str] = mapped_column(String, default=DocumentStatus.UPLOADED.value, nullable=False)
    # Clinical date of the report itself (user-selected at upload, defaults
    # to today) -- distinct from uploaded_at. This is the date ml/'s graph
    # writers attach to every fact extracted from this document, so the AI
    # always has a concrete reference date instead of guessing from raw text.
    report_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(nullable=True)  # chunks indexed into ml/'s Chroma store


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    role: Mapped[str] = mapped_column(String, nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    claims: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # list[Claim] snapshot, if assistant turn
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    chat_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_messages.id"), nullable=True
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default=EvidenceStatus.UNCERTAIN.value, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    source_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    source_span_start: Mapped[int | None] = mapped_column(nullable=True)
    source_span_end: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[str] = mapped_column(String, nullable=False)
    status_code: Mapped[int | None] = mapped_column(nullable=True)
    client_host: Mapped[str | None] = mapped_column(String, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
