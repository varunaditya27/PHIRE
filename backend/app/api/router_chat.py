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

import json
import queue
import threading
from collections.abc import Callable, Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal, get_db
from app.database.schemas import ChatMessage
from app.database.schemas import Claim as ClaimRow
from app.models.claim import Claim
from app.models.response import ChatRequest, ChatResponse
from app.services.gpu_modes import CHAT, gpu_mode
from app.services.ml_singletons import get_qa_chain

router = APIRouter(prefix="/api/chat", tags=["chat"])


def run_chat(db: Session, message: str, on_progress: Callable[[str, str], None] | None = None) -> ChatResponse:
    """The whole chat turn (persist, answer, verify, persist claims), shared by both endpoints."""
    db.add(ChatMessage(role="user", content=message))
    db.commit()

    try:
        # gpu_mode(CHAT): see gpu_modes.py + ml_singletons.py's docstring -- keeps this from
        # racing document ingestion for VRAM.
        with gpu_mode(CHAT, on_progress):
            chain_response = get_qa_chain().answer(message, on_progress=on_progress)
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


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    return run_chat(db, request.message)


def _sse(event: str, data: dict) -> str:
    """One Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Same turn as POST /api/chat, streamed as SSE: `progress` events while
    the pipeline works, then one `result` (the ChatResponse JSON) or `error`.

    The turn runs on its own thread with its own DB session -- the request-
    scoped session from Depends(get_db) is closed when the handler returns,
    before a streaming body finishes -- and hands events back via a queue.
    """
    events: queue.Queue = queue.Queue()

    def work() -> None:
        db = SessionLocal()
        try:
            result = run_chat(db, request.message, lambda stage, msg: events.put(("progress", {"stage": stage, "message": msg})))
            events.put(("result", json.loads(result.model_dump_json())))
        except HTTPException as exc:
            events.put(("error", {"message": exc.detail}))
        except Exception as exc:  # noqa: BLE001 -- reported to the client as an error event
            events.put(("error", {"message": str(exc)}))
        finally:
            db.close()
            events.put(None)

    def stream() -> Iterator[str]:
        threading.Thread(target=work, daemon=True).start()
        yield _sse("progress", {"stage": "start", "message": "Question received"})
        while (item := events.get()) is not None:
            yield _sse(*item)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
