"""Server-Sent Events framing shared by the streaming endpoints (chat stream, document events)."""

import json


def sse_frame(event: str, data: dict) -> str:
    """One SSE frame: `event:` line, JSON `data:` line, blank-line terminator."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
