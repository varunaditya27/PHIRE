"""
GET /api/search/evidence — evidence/document search endpoint.

Thin passthrough into ml.rag.retriever.HybridRetriever (BM25 + semantic
hybrid search, fused via reciprocal rank fusion) -- see
app/api/router_evidence.py's POST /api/evidence/retrieve for the same
underlying call exposed with a request-body contract instead of query
params (kept as two routes per CONTRIBUTING.md's original endpoint list,
not because the logic differs).
"""

from fastapi import APIRouter

from app.models.response import EvidenceCitation
from app.services.citations import chunk_to_citation
from app.services.ml_singletons import get_retriever

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/evidence", response_model=list[EvidenceCitation])
def search_evidence(query: str, top_k: int = 5) -> list[EvidenceCitation]:
    chunks = get_retriever().retrieve(query, top_k=top_k)
    return [chunk_to_citation(chunk) for chunk in chunks]
