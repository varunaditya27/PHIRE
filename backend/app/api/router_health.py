"""
POST /api/health — service liveness/readiness endpoint.

Checks PostgreSQL, Ollama, Chroma (via ml/'s own retriever singleton),
and Neo4j connectivity. Used by docker-compose healthchecks and the
frontend's system-status indicator.
"""

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.connection import get_db
from app.models.response import HealthStatus
from app.services.ml_singletons import get_retriever, new_graph_client

router = APIRouter(tags=["health"])


@router.post("/api/health", response_model=HealthStatus)
def health_check(db: Session = Depends(get_db)) -> HealthStatus:
    settings = get_settings()
    detail: dict[str, str] = {}

    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_ok = False
        detail["database"] = str(exc)

    ollama_ok = True
    try:
        resp = httpx.get(f"{settings.ollama_host}/api/tags", timeout=3.0)
        ollama_ok = resp.status_code == 200
        if not ollama_ok:
            detail["ollama"] = f"status {resp.status_code}"
    except Exception as exc:  # noqa: BLE001
        ollama_ok = False
        detail["ollama"] = str(exc)

    vector_ok = True
    try:
        get_retriever()
    except Exception as exc:  # noqa: BLE001
        vector_ok = False
        detail["vector_store"] = str(exc)

    neo4j_ok = True
    try:
        with new_graph_client() as client:
            client.run("RETURN 1")
    except Exception as exc:  # noqa: BLE001
        neo4j_ok = False
        detail["graph"] = str(exc)

    overall = "ok" if (db_ok and ollama_ok and vector_ok and neo4j_ok) else "degraded"
    return HealthStatus(
        status=overall, database=db_ok, ollama=ollama_ok, vector_store=vector_ok, graph=neo4j_ok, detail=detail
    )
