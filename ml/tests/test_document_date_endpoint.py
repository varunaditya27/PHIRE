"""HTTP-level tests for PUT /api/documents/{id}/date (validation and status handling); the rebuild itself is faked."""

import sys
import uuid
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

backend_path = str(Path(__file__).resolve().parents[2] / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from fastapi.testclient import TestClient

from app.database.connection import get_db
from app.main import app

DOC_ID = uuid.uuid4()


def _client(document):
    session = MagicMock()
    session.get.return_value = document
    app.dependency_overrides[get_db] = lambda: session
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _doc(**overrides):
    base = dict(id=DOC_ID, filename="r.pdf", content_type="application/pdf", status="processed", uploaded_at="2026-10-04T10:00:00Z",
                processed_at=None, error_message=None, document_date="2026-10-04", needs_date=True, extracted_data={"x": 1})
    return SimpleNamespace(**{**base, **overrides})


def test_unknown_document_is_404():
    assert _client(None).put(f"/api/documents/{DOC_ID}/date", json={"document_date": "2026-03-12"}).status_code == 404


def test_future_date_is_rejected_with_422():
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    response = _client(_doc()).put(f"/api/documents/{DOC_ID}/date", json={"document_date": tomorrow})

    assert response.status_code == 422


def test_garbage_date_is_rejected_with_422():
    assert _client(_doc()).put(f"/api/documents/{DOC_ID}/date", json={"document_date": "last tuesday"}).status_code == 422


def test_document_still_processing_is_409():
    response = _client(_doc(status="processing")).put(f"/api/documents/{DOC_ID}/date", json={"document_date": "2026-03-12"})

    assert response.status_code == 409


def test_document_without_a_saved_extraction_is_409_with_guidance():
    response = _client(_doc(extracted_data=None)).put(f"/api/documents/{DOC_ID}/date", json={"document_date": "2026-03-12"})

    assert response.status_code == 409 and "upload it again" in response.json()["detail"]


def test_valid_date_triggers_the_rebuild_and_returns_the_document():
    document = _doc()
    with patch("app.api.router_documents.redate_document") as redate:
        response = _client(document).put(f"/api/documents/{DOC_ID}/date", json={"document_date": "2026-03-12"})

    assert response.status_code == 200
    redate.assert_called_once()
    assert redate.call_args[0][1] is document and redate.call_args[0][2] == "2026-03-12"
    assert response.json()["needs_date"] is True    # the fake redate did not flip it; the real one does (tested above)


# --- DELETE /api/documents/{id}: its own regression tests (it was once lost in a router split, unnoticed) ---

def test_delete_removes_vectors_graph_facts_file_and_row(tmp_path):
    stored = tmp_path / "r.pdf"
    stored.write_bytes(b"%PDF")
    document = _doc(storage_path=str(stored), status="processed")
    session = MagicMock()
    session.get.return_value = document
    app.dependency_overrides[get_db] = lambda: session
    retriever, graph_cm = MagicMock(), MagicMock()
    graph_cm.__enter__.return_value = MagicMock()

    with patch("app.api.router_documents.get_retriever", return_value=retriever), \
         patch("app.api.router_documents.new_graph_client", return_value=graph_cm), \
         patch("ml.graph.deletion.delete_document_facts") as delete_facts:
        response = TestClient(app).delete(f"/api/documents/{DOC_ID}")

    assert response.status_code == 204
    retriever.delete_by_document_id.assert_called_once_with(str(DOC_ID))
    delete_facts.assert_called_once()
    assert not stored.exists()
    session.delete.assert_called_once_with(document)


def test_delete_unknown_is_404_and_processing_is_409():
    assert _client(None).delete(f"/api/documents/{DOC_ID}").status_code == 404
    assert _client(_doc(status="processing")).delete(f"/api/documents/{DOC_ID}").status_code == 409


def test_every_documents_route_the_frontend_calls_is_registered():
    """Guards against a router refactor silently dropping an endpoint (DELETE was lost once)."""
    paths = app.openapi()["paths"]
    for path, methods in {
        "/api/documents": {"get"}, "/api/documents/upload": {"post"},
        "/api/documents/{document_id}": {"get", "delete"}, "/api/documents/{document_id}/date": {"put"},
        "/api/documents/{document_id}/events": {"get"}, "/api/documents/{document_id}/process": {"post"},
        "/api/chat": {"post"}, "/api/chat/stream": {"post"}, "/api/chat/messages": {"get"},
    }.items():
        assert methods <= set(paths[path]), f"{path} is missing {methods - set(paths[path])}"
