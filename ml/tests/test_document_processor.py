import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure backend directory is in sys.path
backend_path = str(Path(__file__).resolve().parents[2] / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Mock sqlalchemy modules if not installed in ml/.venv
sys.modules.setdefault("sqlalchemy", MagicMock())
sys.modules.setdefault("sqlalchemy.orm", MagicMock())
sys.modules.setdefault("sqlalchemy.dialects.postgresql", MagicMock())

from app.services.ml_singletons import get_lift_extractor
from app.services.document_processor import process_document, _rollback_ml_writes
from app.utils.constants import DocumentStatus


@pytest.fixture(autouse=True)
def _no_real_ollama_unload():
    """gpu_mode(LIFT) evicts Ollama's model; never do that to the dev machine from a test."""
    with patch("app.services.gpu_modes._unload_ollama_model"):
        yield


def test_get_lift_extractor_singleton():
    """Verify get_lift_extractor returns a cached LiftExtractor singleton."""
    ext1 = get_lift_extractor()
    ext2 = get_lift_extractor()
    assert ext1 is ext2
    assert hasattr(ext1, "extract")
    assert ext1.model_id == "datalab-to/lift"


def test_process_document_success(monkeypatch, tmp_path):
    """Verify process_document runs Lift extraction, chunking, and graph writes."""
    dummy_file = tmp_path / "report.pdf"
    dummy_file.write_bytes(b"%PDF dummy")

    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.id = "doc-test-123"
    mock_doc.filename = "report.pdf"
    mock_doc.storage_path = str(dummy_file)
    mock_doc.status = DocumentStatus.UPLOADED.value

    mock_payload = {
        "document_date": "2026-03-10",
        "document_type": "Diagnostic Laboratory Report",
        "observations": [
            {
                "name": "LDL Cholesterol",
                "value": "162",
                "unit": "mg/dL",
                "reference_range": "0-100",
                "interpretation": "High",
            }
        ],
        "medications": [
            {
                "name": "Atorvastatin",
                "dosage": "20 mg",
                "frequency": "once daily",
                "status": "active",
            }
        ],
        "conditions": [
            {"name": "Hyperlipidemia", "status": "active"}
        ],
        "narrative_sections": [
            {"heading": "Impression", "content": "Elevated LDL."}
        ],
    }

    mock_chunks = [MagicMock(id="chunk-1", text="Chunk text")]
    mock_retriever = MagicMock()
    mock_graph_client = MagicMock()
    mock_client_cm = MagicMock()
    mock_client_cm.__enter__.return_value = mock_graph_client

    with patch("ml.rag.ingest.patient_documents.extract_document_data", return_value=mock_payload) as mock_extract, \
         patch("ml.rag.ingest.ingest_patient_document.build_chunks", return_value=mock_chunks) as mock_build_chunks, \
         patch("app.services.document_processor.get_retriever", return_value=mock_retriever), \
         patch("app.services.document_processor.new_graph_client", return_value=mock_client_cm), \
         patch("ml.graph.medications.write_medications") as mock_write_meds, \
         patch("ml.graph.conditions.write_conditions") as mock_write_conds, \
         patch("ml.graph.observations.write_observations") as mock_write_obs:

        process_document(mock_db, mock_doc)

        # Extraction called with file path and get_lift_extractor
        mock_extract.assert_called_once()
        extractor_arg = mock_extract.call_args.kwargs.get("extractor")
        assert extractor_arg is get_lift_extractor()

        # Chunks built with payload data, document_id, and the user's original filename
        mock_build_chunks.assert_called_once_with(
            dummy_file, data=mock_payload, document_id="doc-test-123", filename=mock_doc.filename
        )
        mock_retriever.add_documents.assert_called_once_with(mock_chunks)

        # Graph writers called
        mock_write_meds.assert_called_once()
        mock_write_conds.assert_called_once()
        mock_write_obs.assert_called_once()

        # Observations parsed with Lift fields preserved
        written_obs = mock_write_obs.call_args[0][3]
        assert len(written_obs) == 1
        assert written_obs[0]["code"] == "LDL Cholesterol"
        assert written_obs[0]["value"] == 162.0
        assert written_obs[0]["unit"] == "mg/dL"
        assert written_obs[0]["interpretation"] == "High"

        # Document updated
        assert mock_doc.status == DocumentStatus.PROCESSED.value
        assert mock_doc.chunk_count == len(mock_chunks)
        assert mock_doc.processed_at is not None


def test_process_document_failure_rolls_back(tmp_path):
    """Verify failure rolls back DB and ML writes and marks document FAILED."""
    dummy_file = tmp_path / "bad.pdf"
    dummy_file.write_bytes(b"%PDF dummy")

    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.id = "doc-fail-123"
    mock_doc.storage_path = str(dummy_file)

    with patch("ml.rag.ingest.patient_documents.extract_document_data", side_effect=RuntimeError("Extraction crashed")), \
         patch("app.services.document_processor._rollback_ml_writes") as mock_rollback_ml:

        with pytest.raises(RuntimeError, match="Extraction crashed"):
            process_document(mock_db, mock_doc)

        mock_db.rollback.assert_called_once()
        mock_rollback_ml.assert_called_once_with("doc-fail-123")
        assert mock_doc.status == DocumentStatus.FAILED.value
        assert "Extraction crashed" in mock_doc.error_message


def test_rollback_ml_writes():
    """Verify _rollback_ml_writes invokes retriever and graph deletion safely."""
    mock_retriever = MagicMock()
    mock_graph_client = MagicMock()
    mock_client_cm = MagicMock()
    mock_client_cm.__enter__.return_value = mock_graph_client

    with patch("app.services.document_processor.get_retriever", return_value=mock_retriever), \
         patch("app.services.document_processor.new_graph_client", return_value=mock_client_cm), \
         patch("ml.graph.deletion.delete_document_facts") as mock_del_facts:

        _rollback_ml_writes("doc-123")

        mock_retriever.delete_by_document_id.assert_called_once_with("doc-123")
        mock_del_facts.assert_called_once_with(mock_graph_client, "doc-123")


def test_preload_ml_modules_imports_the_heavy_modules_up_front():
    import sys

    from app.services.ml_singletons import preload_ml_modules

    preload_ml_modules()

    for name in ("ml.rag.retriever", "ml.claims.verifier", "ml.chains.qa_chain", "ml.rag.ingest.lift_extractor"):
        assert name in sys.modules


def test_rollback_builds_the_retriever_under_the_gpu_lock():
    """get_retriever() may construct Chroma + embedding models; it must not race a chat request doing the same."""
    from unittest.mock import call

    events = []

    class FakeMode:
        def __enter__(self):
            events.append("enter")

        def __exit__(self, *exc):
            events.append("exit")

    retriever = MagicMock()
    retriever.delete_by_document_id.side_effect = lambda doc_id: events.append("delete")
    with patch("app.services.document_processor.gpu_mode", return_value=FakeMode()), \
         patch("app.services.document_processor.get_retriever", return_value=retriever), \
         patch("app.services.document_processor.new_graph_client"), \
         patch("ml.graph.deletion.delete_document_facts"):
        _rollback_ml_writes("doc-1")

    assert events == ["enter", "delete", "exit"]
