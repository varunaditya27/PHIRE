"""
Pydantic schemas for API responses.

Standard envelope for chat responses: answer text + list of Claim objects
+ evidence citations, so the frontend can render inline source
highlighting.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.claim import Claim


class EvidenceCitation(BaseModel):
    # str, not UUID: ml/rag/retriever.py's Chunk.id is a source-derived
    # string (e.g. "patient_doc_<hash>_0", "medlineplus_...") for real
    # ml/-backed evidence, not a database UUID.
    evidence_passage_id: str
    document_id: str | None = None
    text: str
    source_url: str | None = None
    source_filename: str | None = None
    authority: float | None = None
    page_number: int | None = None
    score: float | None = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    id: UUID | None = None
    answer: str
    claims: list[Claim] = []
    citations: list[EvidenceCitation] = []
    created_at: datetime | None = None


class ChatMessageRead(BaseModel):
    """One persisted chat turn, for rehydrating the chat UI after a reload."""

    id: UUID
    role: str
    content: str
    claims: list[Claim] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceRetrieveRequest(BaseModel):
    query: str
    top_k: int = 5


class EvidenceRetrieveResponse(BaseModel):
    citations: list[EvidenceCitation]


class EvidenceVerifyRequest(BaseModel):
    # No evidence_passage_ids field: /verify re-retrieves its own evidence
    # from the claim text (see router_evidence.py's verify_claim) rather
    # than taking passage ids to look up -- ml/'s Chunk objects have no
    # backend database row a UUID could reference.
    claim: str


class EvidenceVerifyResponse(BaseModel):
    claim: Claim


class HealthStatus(BaseModel):
    status: str
    database: bool
    ollama: bool
    vector_store: bool
    graph: bool
    detail: dict[str, str] = {}
