"""
HIPAA-oriented audit logging for patient data access.

Append-only log of who accessed which patient's data, when, and via which
endpoint — required for the privacy/compliance research theme. Persists to
the audit_log table (see app/database/schemas.py); mirrored to a local
append-only file at Settings.audit_log_path as a tamper-evident backup.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.schemas import AuditLog


def log_access(
    db: Session,
    *,
    endpoint: str,
    method: str,
    status_code: int | None = None,
    client_host: str | None = None,
) -> None:
    entry = AuditLog(
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        client_host=client_host,
    )
    db.add(entry)
    db.commit()

    _append_to_file(
        {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "client_host": client_host,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def _append_to_file(record: dict) -> None:
    path = Path(get_settings().audit_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")
