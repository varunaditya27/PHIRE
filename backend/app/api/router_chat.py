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
from app.services.intent_classifier import classify_intent, Intent
from app.utils.constants import EvidenceStatus
from ml.graph.patient_context import get_current_patient_facts, get_topic_marker_facts
from ml.graph.reference_ranges import TOPIC_MARKERS, detect_topic
from app.services.ml_singletons import new_graph_client

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    db.add(ChatMessage(role="user", content=request.message))
    db.commit()

    # Topic short-circuit: a question naming a known health topic ("do I
    # have diabetes", "is my thyroid normal") is answered by directly
    # checking exactly the markers that matter for it (see
    # ml.graph.reference_ranges.TOPIC_MARKERS/detect_topic), not by
    # sending the whole patient panel + question to the LLM and hoping it
    # stays on-topic -- found live: for a report that doesn't cover the
    # asked-about topic, the LLM would instead narrate unrelated markers
    # from whatever panel the patient does have. This runs before intent
    # classification/QAChain entirely, and needs no LLM call: the
    # value-vs-range check is exact, so every fact here is DERIVED at
    # full confidence, not something for NLI to confirm.
    topic = detect_topic(request.message)
    if topic is not None:
        facts, missing = get_topic_marker_facts(new_graph_client(), topic)
        answer_parts = list(facts)
        if missing:
            answer_parts.append(f"Your uploaded reports don't include a result for: {', '.join(missing)}.")
        answer = " ".join(answer_parts)
        claims = [
            Claim(statement=f, status=EvidenceStatus.DERIVED, confidence=1.0)
            for f in facts
        ]
        assistant_message = ChatMessage(role="assistant", content=answer, claims=[c.model_dump() for c in claims])
        db.add(assistant_message)
        db.flush()
        for claim in claims:
            db.add(ClaimRow(chat_message_id=assistant_message.id, statement=claim.statement, status=claim.status.value, confidence=claim.confidence))
        db.commit()
        return ChatResponse(id=assistant_message.id, answer=answer, claims=claims, created_at=assistant_message.created_at)

    intent = classify_intent(request.message)
    if intent == Intent.DIAGNOSIS_REQUEST:
        msg = "I cannot provide medical diagnoses. Please consult a qualified healthcare professional."
        assistant_message = ChatMessage(role="assistant", content=msg)
        db.add(assistant_message)
        db.commit()
        return ChatResponse(id=assistant_message.id, answer=msg, claims=[], created_at=assistant_message.created_at)

    if intent in (Intent.DATA_LOOKUP, Intent.TREND_ANALYSIS, Intent.HEALTH_INTERPRETATION):
        facts = get_current_patient_facts(new_graph_client())
        if not facts:
            msg = "I cannot answer this as I don't have access to your patient context."
            assistant_message = ChatMessage(role="assistant", content=msg)
            db.add(assistant_message)
            db.commit()
            return ChatResponse(id=assistant_message.id, answer=msg, claims=[], created_at=assistant_message.created_at)

    try:
        # GPU_LOCK: see ml_singletons.py's docstring -- keeps this from
        # racing document ingestion for VRAM.
        with GPU_LOCK:
            chain_response = get_qa_chain().answer(request.message)
    except Exception as exc:  # noqa: BLE001 -- surfaced to the caller, not swallowed
        # Still records an assistant turn (error_message, no claims) so
        # this exchange isn't an orphaned user question with no reply --
        # the module docstring's "every exchange is persisted regardless
        # of outcome" wasn't actually true for a pipeline failure before
        # this (found via review): only the user message above had
        # already been committed, and this except returned before ever
        # writing an assistant ChatMessage.
        db.add(ChatMessage(role="assistant", content=f"[error] ml pipeline failed: {exc}"))
        db.commit()
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
