"""Tests for scripts/reset_data.py's Chroma and file resets, on temporary directories only (never real data)."""

import importlib.util
import sys
from pathlib import Path

import chromadb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO_ROOT), str(REPO_ROOT / "backend")]
spec = importlib.util.spec_from_file_location("reset_data", REPO_ROOT / "scripts" / "reset_data.py")
reset_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reset_data)


def _seed(tmp_path):
    store = tmp_path / "chroma"
    col = chromadb.PersistentClient(path=str(store)).get_or_create_collection("test_collection")
    col.add(
        ids=["p1", "p2", "r1"], documents=["a", "b", "test_collection"], embeddings=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]],
        metadatas=[{"source": "patient_document"}, {"source": "patient_document"}, {"source": "medlineplus"}],
    )
    manifest = tmp_path / "ingest_manifest.json"
    manifest.write_text("{}")
    return store, col, manifest


def test_patient_only_reset_keeps_reference_chunks_and_manifest(tmp_path):
    store, col, manifest = _seed(tmp_path)

    reset_data.reset_chroma(store, "test_collection", include_reference=False, dry_run=False)

    assert col.get(include=[])["ids"] == ["r1"]
    assert manifest.exists()


def test_include_reference_wipes_everything_and_only_this_stores_manifest(tmp_path):
    store, col, manifest = _seed(tmp_path)
    unrelated = tmp_path.parent / "ingest_manifest.json"  # another store's manifest must be left alone
    existed_before = unrelated.exists()

    reset_data.reset_chroma(store, "test_collection", include_reference=True, dry_run=False)

    assert col.count() == 0
    assert not manifest.exists()
    assert unrelated.exists() == existed_before


def test_dry_run_changes_nothing(tmp_path):
    store, col, manifest = _seed(tmp_path)
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "a.pdf").write_text("x")
    audit = tmp_path / "audit.log"
    audit.write_text("line")

    reset_data.reset_chroma(store, "test_collection", include_reference=True, dry_run=True)
    reset_data.reset_files(uploads, audit, dry_run=True)

    assert col.count() == 3 and manifest.exists()
    assert (uploads / "a.pdf").exists() and audit.read_text() == "line"


def test_reset_files_deletes_uploads_and_truncates_audit_unless_kept(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "a.pdf").write_text("x")
    audit = tmp_path / "audit.log"
    audit.write_text("line")

    reset_data.reset_files(uploads, None, dry_run=False)  # audit kept
    assert not (uploads / "a.pdf").exists() and audit.read_text() == "line"

    reset_data.reset_files(uploads, audit, dry_run=False)
    assert audit.read_text() == ""
