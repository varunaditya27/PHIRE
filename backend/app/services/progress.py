"""
In-process progress channel for document ingestion, consumed by SSE.

Ingestion runs on a BackgroundTasks worker thread while the browser watches
over GET /api/documents/{id}/events, so the two sides need a shared place
to meet. Each document gets an append-only event list plus a Condition;
subscribers replay history first (so a client that connects late, or
reconnects, still sees every stage) and then block for new events.
Single-process only -- fine for PHIRE's single-user local deployment.
"""

import threading
from collections.abc import Iterator
from dataclasses import dataclass, field

HEARTBEAT_SECONDS = 15


@dataclass
class _Channel:
    events: list[dict] = field(default_factory=list)
    done: bool = False
    cond: threading.Condition = field(default_factory=threading.Condition)


_channels: dict[str, _Channel] = {}
_lock = threading.Lock()


def _channel(key: str) -> _Channel:
    with _lock:
        return _channels.setdefault(key, _Channel())


def reset(key: str) -> None:
    """Start a fresh event history, e.g. when a document is (re)processed."""
    with _lock:
        _channels[key] = _Channel()


def forget(key: str) -> None:
    """Drop a deleted document's channel so the dict doesn't grow forever."""
    with _lock:
        _channels.pop(key, None)


def publish(key: str, stage: str, message: str, *, final: bool = False) -> None:
    """Append one progress event; `final=True` marks the stream complete."""
    channel = _channel(key)
    with channel.cond:
        channel.events.append({"stage": stage, "message": message})
        channel.done = final
        channel.cond.notify_all()


def has_history(key: str) -> bool:
    """Whether any event was published for `key` in this process."""
    with _lock:
        return key in _channels and bool(_channels[key].events)


def subscribe(key: str) -> Iterator[dict | None]:
    """Yield every event (history, then live) until final; None is a heartbeat tick."""
    channel = _channel(key)
    index = 0
    while True:
        with channel.cond:
            while index >= len(channel.events) and not channel.done:
                if not channel.cond.wait(timeout=HEARTBEAT_SECONDS):
                    yield None
            pending = channel.events[index:]
            index = len(channel.events)
            finished = channel.done
        yield from pending
        if finished:
            return
