"""
Shared evidence search for GET /api/search/evidence and POST /api/evidence/retrieve.

Retrieves a wide candidate pool, reranks it the same way chat does, and
returns citations carrying the cross-encoder relevance as `score` -- the
only 0-1 relevance signal in the system (the retriever's fused rank has no
score, which is why the Search UI used to show 0.0%).
"""

from app.models.response import EvidenceCitation
from app.services.citations import chunk_to_citation
from app.services.gpu_modes import CHAT, gpu_mode
from app.services.ml_singletons import get_reranker, get_retriever

CANDIDATE_MULTIPLIER = 4
MIN_CANDIDATES = 20


def search_evidence(query: str, top_k: int) -> list[EvidenceCitation]:
    """Top-k reranked evidence for `query`, each with its relevance score."""
    with gpu_mode(CHAT):
        candidates = get_retriever().retrieve(query, top_k=max(MIN_CANDIDATES, top_k * CANDIDATE_MULTIPLIER))
        reranker = get_reranker()
        ranked = reranker.rerank(query, candidates, top_k=top_k)
        scores = reranker.score(query, ranked)
    return [chunk_to_citation(chunk, score) for chunk, score in zip(ranked, scores)]
