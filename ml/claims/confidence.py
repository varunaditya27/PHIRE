"""
Confidence scoring for verified claims.

Combines three signals into one value per claim: how strongly the
evidence entails (or contradicts) it, how highly that evidence ranked at
retrieval time, and how authoritative its source is. Entailment dominates
the weighting since it's the only signal grounded in whether the evidence
actually supports *this specific claim* — retrieval rank and authority
describe the evidence in general, not its relevance to this claim.
"""

ENTAILMENT_WEIGHT = 0.5
RETRIEVAL_WEIGHT = 0.25
AUTHORITY_WEIGHT = 0.25


def compute_confidence(entailment_prob: float, contradiction_prob: float, retrieval_rank: int, authority: float) -> float:
    """Combine a claim's verification signals into a single [0, 1] confidence value.

    retrieval_rank is the 0-indexed position of the evidence chunk among
    HybridRetriever/Reranker's results (0 = best match) — retriever.py and
    reranker.py return ranked chunks, not exposed numeric scores, so rank
    position is the retrieval-strength signal actually available to
    callers (ml/chains/qa_chain.py), consistent with how reranker.py
    already turns rank/recency into a decayed score.
    """
    net_entailment = max(entailment_prob - contradiction_prob, 0.0)
    retrieval_score = 1.0 / (retrieval_rank + 1)
    confidence = (
        ENTAILMENT_WEIGHT * net_entailment
        + RETRIEVAL_WEIGHT * retrieval_score
        + AUTHORITY_WEIGHT * authority
    )
    return max(0.0, min(1.0, confidence))
