"""
Security and compliance utilities: encryption at rest, request auth,
audit-logging hooks.

Enforces that no patient health data leaves the local network (no
outbound calls to third-party APIs from this process) and wires
request-level audit trail hooks. Field-level encryption/decryption
helpers live in utils/encryption.py; the log sink lives in
services/audit_logger.py.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ml.local_only import require_localhost

from app.database.connection import SessionLocal
from app.services.audit_logger import log_access

# Privacy boundary: every outbound network call this process makes must
# resolve to localhost (local Ollama; local Postgres via SQLAlchemy isn't
# HTTP so isn't covered here). Delegates to ml/local_only.py's
# require_localhost() -- the same check ml.llm.ollama_client.OllamaClient
# and ml.graph.client.GraphClient already enforce for their own calls --
# instead of maintaining a second hand-written hostname allowlist here.
# A prior version of this file reimplemented the check independently and
# had already drifted from ml/'s canonical allowlist (an extra "0.0.0.0"
# entry not present there); importing the one implementation means a
# future fix to the shared logic can't fail to propagate here.


def is_outbound_host_allowed(host: str) -> bool:
    """True iff host's actual hostname (not a substring match) is local."""
    try:
        require_localhost(host if "//" in host else f"//{host}")
        return True
    except ValueError:
        return False


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
                except Exception as exc:  # noqa: BLE001 -- a logging failure (e.g.
                    # disk full) must not replace the real response/exception
                    # this finally block is already propagating; best-effort
                    # print so the failure is still visible somewhere.
                    print(f"AuditMiddleware: failed to write audit log entry: {exc}")
                finally:
                    db.close()
