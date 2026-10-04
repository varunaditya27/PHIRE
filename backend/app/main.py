"""
FastAPI application entry point.

Configures CORS for the local-only frontend (no public internet exposure
by default), registers all routers, and wires the audit-logging
middleware. No request-handling logic belongs here — this file only
assembles the app.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    router_chat,
    router_claims,
    router_documents,
    router_evidence,
    router_health,
    router_observations,
    router_recommendations,
    router_search,
)
from app.config import get_settings
from app.security import AuditMiddleware
from app.services.ml_singletons import preload_ml_modules

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Import ml/'s heavy modules before serving (see preload_ml_modules)."""
    preload_ml_modules()
    yield


app = FastAPI(
    title="PHIRE Backend",
    description="Privacy-preserving, evidence-attributed healthcare AI — local-only API.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditMiddleware)

app.include_router(router_health.router)
app.include_router(router_documents.router)
app.include_router(router_observations.router)
app.include_router(router_search.router)
app.include_router(router_chat.router)
app.include_router(router_claims.router)
app.include_router(router_evidence.router)
app.include_router(router_recommendations.router)


@app.get("/api/ping", tags=["health"])
def ping() -> dict[str, str]:
    return {"status": "ok"}
