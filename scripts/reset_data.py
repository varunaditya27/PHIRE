#!/usr/bin/env python3
"""
Reset PHIRE to a clean slate so a real user can start from nothing and
ingest only their own health records.

Wipes, across every store the backend writes to:
  - PostgreSQL: documents, chat_messages, claims (+ audit_log unless --keep-audit)
  - Neo4j:      the whole Longitudinal Health Graph (all nodes and relationships)
  - Chroma:     patient-document chunks only -- the public reference corpus
                (MedlinePlus/PubMed/USDA) is kept unless --include-reference
  - Disk:       uploaded files, and the audit log file unless --keep-audit

Targets come from backend/.env (the same settings the backend uses), and are
printed before anything happens -- check them, other projects may share this
machine's databases. Restart the backend afterwards: its retriever caches
chunks in memory.

Run from the repo root:
  PYTHONPATH=. ml/.venv/bin/python scripts/reset_data.py --dry-run
  PYTHONPATH=. ml/.venv/bin/python scripts/reset_data.py            # asks you to type RESET
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path[:0] = [str(REPO_ROOT), str(BACKEND_DIR)]

import chromadb  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app.config import get_settings  # noqa: E402
from ml.graph.client import GraphClient  # noqa: E402

PATIENT_CHUNK_FILTER = {"source": "patient_document"}
PATIENT_TABLES = ["claims", "chat_messages", "documents"]


def backend_path(raw: str) -> Path:
    """Resolve a settings path the way the backend does: relative to backend/ (its working directory)."""
    path = Path(raw)
    return path if path.is_absolute() else (BACKEND_DIR / path).resolve()


def reset_postgres(url: str, tables: list[str], dry_run: bool) -> str:
    """Empty `tables` (cascading, ids restarted); keeps the schema and alembic_version."""
    engine = create_engine(url)
    with engine.begin() as conn:
        counts = {t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar() for t in tables}
        if not dry_run:
            conn.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
    return ", ".join(f"{t}={n}" for t, n in counts.items())


def reset_neo4j(uri: str, user: str, password: str, dry_run: bool) -> str:
    """Delete every node and relationship in the graph."""
    with GraphClient(uri=uri, user=user, password=password) as client:
        nodes = client.run("MATCH (n) RETURN count(n) AS n")[0]["n"]
        if not dry_run:
            client.run("MATCH (n) DETACH DELETE n")
    return f"nodes={nodes}"


def reset_chroma(path: Path, collection: str, include_reference: bool, dry_run: bool) -> str:
    """Delete patient-document chunks (or every chunk with --include-reference)."""
    col = chromadb.PersistentClient(path=str(path)).get_or_create_collection(collection)
    total = col.count()
    ids = col.get(include=[])["ids"] if include_reference else col.get(where=PATIENT_CHUNK_FILTER, include=[])["ids"]
    if ids and not dry_run:
        col.delete(ids=ids)
    if include_reference and not dry_run:
        # run_ingest.py writes its manifest next to the Chroma dir; remove the one belonging to *this* store.
        (path.parent / "ingest_manifest.json").unlink(missing_ok=True)
    return f"deleting {len(ids)} of {total} chunks ({'all' if include_reference else 'patient documents only'})"


def reset_files(upload_dir: Path, audit_log: Path | None, dry_run: bool) -> str:
    """Delete uploaded files and (optionally) truncate the audit log file."""
    uploads = [p for p in upload_dir.glob("*") if p.is_file()] if upload_dir.is_dir() else []
    if not dry_run:
        for p in uploads:
            p.unlink()
        if audit_log and audit_log.exists():
            audit_log.write_text("")
    return f"uploads={len(uploads)}, audit_log={'truncated' if audit_log else 'kept'}"


def _confirm() -> str:
    """The user's typed confirmation; empty when there is no terminal (so scripts must pass --yes)."""
    try:
        return input("Type RESET to delete all of the above: ").strip()
    except EOFError:
        return ""


def main() -> int:
    """Parse flags, show targets, confirm, then wipe each store, reporting per-store success."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="show what would be deleted; change nothing")
    parser.add_argument("--yes", action="store_true", help="skip the typed confirmation")
    parser.add_argument("--include-reference", action="store_true", help="also wipe the public reference corpus")
    parser.add_argument("--keep-audit", action="store_true", help="keep audit_log rows and the audit log file")
    args = parser.parse_args()

    s = get_settings()
    chroma_path, upload_dir = Path(s.chroma_persist_dir), backend_path(s.upload_dir)
    audit_log = None if args.keep_audit else backend_path(s.audit_log_path)
    tables = PATIENT_TABLES + ([] if args.keep_audit else ["audit_log"])

    print("PHIRE reset" + (" (DRY RUN)" if args.dry_run else ""))
    print(f"  postgres : {s.database_url.split('@')[-1]}  tables: {', '.join(tables)}")
    print(f"  neo4j    : {s.neo4j_uri}  (entire graph)")
    print(f"  chroma   : {chroma_path}  collection {s.chroma_collection}")
    print(f"  uploads  : {upload_dir}")
    if not args.dry_run and not args.yes and _confirm() != "RESET":
        print("Aborted; nothing changed.")
        return 1

    steps = {
        "postgres": lambda: reset_postgres(s.database_url, tables, args.dry_run),
        "neo4j": lambda: reset_neo4j(s.neo4j_uri, s.neo4j_user, s.neo4j_password, args.dry_run),
        "chroma": lambda: reset_chroma(chroma_path, s.chroma_collection, args.include_reference, args.dry_run),
        "files": lambda: reset_files(upload_dir, audit_log, args.dry_run),
    }
    failed = 0
    for name, step in steps.items():
        try:
            print(f"  [ok]   {name}: {step()}")
        except Exception as exc:  # noqa: BLE001 -- report, keep going so one down store doesn't block the rest
            failed += 1
            print(f"  [FAIL] {name}: {exc}")
    print("Done. Restart the backend so its in-memory caches are rebuilt." if not failed else f"{failed} store(s) failed; re-run once fixed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
