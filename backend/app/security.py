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


# Endpoints that touch patient data — audited on every request. Includes
# /api/search: router_search.py's /api/search/evidence is a GET passthrough
# to the same underlying evidence-retrieval call as the audited
# /api/evidence/retrieve, so it needs the same audit coverage.
_AUDITED_PREFIXES = (
    "/api/observations", "/api/timeline", "/api/documents", "/api/chat",
    "/api/evidence", "/api/claims", "/api/search",
)


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Logged in a finally so a route/dependency exception (e.g. an
        # unhandled Neo4j driver error) still leaves an audit trail instead
        # of silently skipping it -- status_code is None in that case since
        # call_next never returned a response.
        status_code = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            if request.url.path.startswith(_AUDITED_PREFIXES):
                db = SessionLocal()
                try:
                    log_access(
                        db,
                        endpoint=request.url.path,
                        method=request.method,
                        status_code=status_code,
                        client_host=request.client.host if request.client else None,
                    )
                finally:
                    db.close()
