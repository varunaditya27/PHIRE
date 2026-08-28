"""
Pydantic schemas for generated claims and their evidence status.

Claim: generated statement, its evidence status, and a citation back to
the exact source. Mirrors ml.chains.qa_chain.VerifiedClaim's fields
directly rather than a passage/observation UUID list -- ml/'s evidence
chunks (ml/rag/retriever.py's Chunk) are keyed by source-derived string
ids, not backend database UUIDs, and a claim's citation is either a
document char-span, a reference URL, or a patient-graph fact, not a row
in evidence_passages.

status is one of {SUPPORTED, DERIVED, INFERRED, UNCERTAIN, CONFLICTING,
UNSUPPORTED} -- INFERRED is reserved for future multi-hop reasoning
support; ml/claims/verifier.py never produces it today (see its
docstring).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.utils.constants import EvidenceStatus


class Claim(BaseModel):
    id: UUID | None = None
    statement: str
    status: EvidenceStatus
    confidence: float | None = None
    source_url: str | None = None
    source_filename: str | None = None
    source_span: tuple[int, int] | None = None


class ClaimRead(Claim):
    id: UUID
    chat_message_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ClaimExtractRequest(BaseModel):
    text: str


class ClaimExtractResponse(BaseModel):
    claims: list[Claim]
