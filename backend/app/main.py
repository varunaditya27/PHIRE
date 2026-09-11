"""
FastAPI application entry point.

Configures CORS for the local-only frontend (no public internet exposure
by default), registers all routers, and wires the audit-logging
middleware. No request-handling logic belongs here — this file only
assembles the app.
"""

import threading

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

settings = get_settings()

app = FastAPI(
    title="PHIRE Backend",
    description="Privacy-preserving, evidence-attributed healthcare AI — local-only API.",
    version="0.1.0",
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


@app.on_event("startup")
def _warm_up_models() -> None:
    """Load every local model + touch Ollama once in the background at
    startup, instead of paying that cost on whichever request happens to
    arrive first. Each of retriever/reranker/verifier/ollama_client is a
    real model load (MedCPT embeddings, MedCPT cross-encoder, bart-large-
    mnli, plus Ollama's own model-into-GPU-memory load) -- lru_cache means
    the first caller pays for all of them at once, which is exactly what
    made the first chat message after a restart take minutes. Backgrounded
    (not awaited) so /api/health responds immediately; a chat request that
    lands mid-warm-up still just pays for whatever isn't done yet, same as
    before this existed -- this only removes the "guaranteed worst case
    is the very first request" part.
    """
    def _warm_up() -> None:
        from app.services.ml_singletons import get_qa_chain

        try:
            chain = get_qa_chain()
            chain._llm.generate("Say OK.")  # forces the chat model into GPU memory now, not on first real message
        except Exception as exc:  # noqa: BLE001 -- best-effort; a real request will surface any real problem
            print(f"[Startup] Model warm-up failed (will load lazily on first request instead): {exc}")

    threading.Thread(target=_warm_up, daemon=True).start()


@app.get("/api/ping", tags=["health"])
def ping() -> dict[str, str]:
    return {"status": "ok"}
