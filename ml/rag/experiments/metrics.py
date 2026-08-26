"""
Standard IR metrics for the embedding-model-selection benchmark: Recall@k
and Mean Reciprocal Rank, computed against the relevance judgments in
eval_data.py.
"""


def recall_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Fraction of relevant ids present in the top-k ranked results."""
    if not relevant_ids:
        return 0.0
    top_k = set(ranked_ids[:k])
    return len(top_k & relevant_ids) / len(relevant_ids)


def reciprocal_rank(ranked_ids: list[str], relevant_ids: set[str]) -> float:
    """1/rank of the first relevant id found; 0 if none appear."""
    for rank, doc_id in enumerate(ranked_ids, start=1):
        if doc_id in relevant_ids:
            return 1.0 / rank
    return 0.0
