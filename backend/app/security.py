"""
Security and compliance utilities: encryption at rest, request auth,
audit-logging hooks.

Enforces that no patient health data leaves the local network (no
outbound calls to third-party APIs from this process) and wires
request-level audit trail hooks. Field-level encryption/decryption
helpers live in utils/encryption.py; the log sink lives in
services/audit_logger.py.
"""

from urllib.parse import urlparse

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.database.connection import SessionLocal
from app.services.audit_logger import log_access

# Privacy boundary: every outbound network call this process makes must
# target one of these hosts (local Ollama, local Postgres via SQLAlchemy —
# not HTTP so not listed here). No cloud LLM/API hostnames are ever added.
#
# Same enforcement approach as ml/local_only.py's require_localhost():
# parse the URI and check its hostname component, not the raw string.
# A prior version here used str.startswith() on the raw host string,
# which a hostname like "localhost.attacker.example" satisfies while
# resolving to a genuinely remote host -- the exact bypass ml/local_only.py
# was written to close.
ALLOWED_OUTBOUND_HOSTNAMES = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def is_outbound_host_allowed(host: str) -> bool:
    """True iff host's actual hostname (not a substring match) is local."""
    parsed_hostname = urlparse(host if "//" in host else f"//{host}").hostname
    return parsed_hostname in ALLOWED_OUTBOUND_HOSTNAMES


# Endpoints that touch patient data — audited on every request.
_AUDITED_PREFIXES = (
    "/api/observations", "/api/timeline", "/api/documents", "/api/chat", "/api/evidence", "/api/claims",
)


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.url.path.startswith(_AUDITED_PREFIXES):
            db = SessionLocal()
            try:
                log_access(
                    db,
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    client_host=request.client.host if request.client else None,
                )
            finally:
                db.close()

        return response
