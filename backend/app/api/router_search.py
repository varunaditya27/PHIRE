"""
GET /api/search/evidence — evidence/document search endpoint.

Hybrid retrieval (BM25 + semantic, reciprocal rank fusion) followed by the
same cross-encoder rerank chat uses; each result carries its relevance as
`score` (see app/services/evidence_search.py). See
app/api/router_evidence.py's POST /api/evidence/retrieve for the same
underlying call exposed with a request-body contract instead of query
params (kept as two routes per CONTRIBUTING.md's original endpoint list,
not because the logic differs).
"""

from fastapi import APIRouter

from app.models.response import EvidenceCitation
from app.services import evidence_search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/evidence", response_model=list[EvidenceCitation])
def search_evidence(query: str, top_k: int = 5) -> list[EvidenceCitation]:
    return evidence_search.search_evidence(query, top_k)
