"""Unit tests for backend/app/services/progress.py's replay-then-live event channel."""

import sys
import threading
from pathlib import Path

backend_path = str(Path(__file__).resolve().parents[2] / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services import progress


def test_subscriber_replays_history_then_stops_at_final_event():
    progress.reset("doc-a")
    progress.publish("doc-a", "queued", "waiting")
    progress.publish("doc-a", "extract", "reading")
    progress.publish("doc-a", "processed", "done", final=True)

    assert [e["stage"] for e in progress.subscribe("doc-a")] == ["queued", "extract", "processed"]


def test_late_subscriber_receives_live_events_from_another_thread():
    progress.reset("doc-b")
    progress.publish("doc-b", "queued", "waiting")
    threading.Timer(0.1, progress.publish, args=("doc-b", "processed", "done"), kwargs={"final": True}).start()

    assert [e["stage"] for e in progress.subscribe("doc-b")] == ["queued", "processed"]


def test_reset_discards_previous_run_history():
    progress.reset("doc-c")
    progress.publish("doc-c", "failed", "boom", final=True)
    progress.reset("doc-c")

    assert not progress.has_history("doc-c")


def test_idle_stream_yields_heartbeat_none(monkeypatch):
    monkeypatch.setattr(progress, "HEARTBEAT_SECONDS", 0.05)
    progress.reset("doc-d")
    stream = progress.subscribe("doc-d")

    assert next(stream) is None
    progress.publish("doc-d", "processed", "done", final=True)
    assert next(stream)["stage"] == "processed"
