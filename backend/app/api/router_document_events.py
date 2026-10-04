"""
GET /api/documents/{id}/events -- live ingestion progress for one document, as Server-Sent Events.

Kept apart from router_documents.py (file size) but under the same /api/documents prefix. The
channel itself is app/services/progress.py: process_document publishes stages, this replays history
then streams live events until the terminal `processed`/`failed`.
"""

import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import Document
from app.services import progress
from app.utils.sse import sse_frame

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("/{document_id}/events")
def document_events(document_id: uuid.UUID, db: Session = Depends(get_db)) -> StreamingResponse:
    """SSE stream of this document's ingestion stages, ending with processed/failed.

    A document with no in-memory history (e.g. a backend restart wiped it)
    gets one event reflecting its stored status and the stream closes --
    nothing will ever publish for it, so waiting would just hang.
    """
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    key = str(document_id)
    stored_status, stored_error = document.status, document.error_message

    def stream() -> Iterator[str]:
        if not progress.has_history(key):
            yield sse_frame("progress", {"stage": stored_status, "message": stored_error or stored_status.capitalize()})
            return
        for event in progress.subscribe(key):
            yield ": keep-alive\n\n" if event is None else sse_frame("progress", event)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
