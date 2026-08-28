"""
POST /api/chat — conversational Q&A endpoint.

Calls ml.chains.qa_chain.QAChain (retrieve -> rerank -> generate -> extract
claims -> verify -> abstain-if-unsupported) with the user's question and
returns its answer plus full claim-level evidence attribution -- PHIRE's
core differentiator, not just free text.

QAChain.answer() is a single blocking call (no token streaming -- see its
docstring), so this endpoint returns one JSON response once it's done,
not an SSE stream. The chain instance itself is a shared singleton (see
app/services/ml_singletons.py) built once and reused across requests.

Every exchange is persisted to ChatMessage regardless of outcome,
including the no-evidence abstention message QAChain returns when no
claim clears its confidence threshold.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import ChatMessage
from app.database.schemas import Claim as ClaimRow
from app.models.claim import Claim
from app.models.response import ChatRequest, ChatResponse
from app.services.ml_singletons import GPU_LOCK, get_qa_chain

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    db.add(ChatMessage(role="user", content=request.message))
    db.commit()

    try:
        # GPU_LOCK: see ml_singletons.py's docstring -- keeps this from
        # racing document ingestion for VRAM.
        with GPU_LOCK:
            chain_response = get_qa_chain().answer(request.message)
    except Exception as exc:  # noqa: BLE001 -- surfaced to the caller, not swallowed
        raise HTTPException(status_code=502, detail=f"ml pipeline failed: {exc}") from exc

    claims = [
        Claim(
            statement=c.claim,
            status=c.status,
            confidence=c.confidence,
            source_url=c.source_url,
            source_filename=c.source_filename,
            source_span=c.source_span,
        )
        for c in chain_response.claims
    ]

    assistant_message = ChatMessage(
        role="assistant",
        content=chain_response.answer,
        claims=[c.model_dump() for c in claims],
    )
    db.add(assistant_message)
    db.flush()  # assigns assistant_message.id without a second round trip

    # Also persisted as individual rows (not just the JSON snapshot above)
    # so claims are queryable in SQL -- e.g. for evaluation/analytics --
    # without parsing every chat_messages.claims blob.
    for claim in claims:
        db.add(
            ClaimRow(
                chat_message_id=assistant_message.id,
                statement=claim.statement,
                status=claim.status.value,
                confidence=claim.confidence,
                source_url=claim.source_url,
                source_filename=claim.source_filename,
                source_span_start=claim.source_span[0] if claim.source_span else None,
                source_span_end=claim.source_span[1] if claim.source_span else None,
            )
        )
    db.commit()

    return ChatResponse(
        id=assistant_message.id,
        answer=chain_response.answer,
        claims=claims,
        created_at=assistant_message.created_at,
    )
