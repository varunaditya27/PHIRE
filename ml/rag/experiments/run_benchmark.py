"""
Embedding-model-selection benchmark.

Ranks each candidate in candidates.py against the hand-labeled queries in
eval_data/ using pure cosine similarity (no BM25/fusion — this isolates
embedding quality specifically, since retriever.py's BM25 leg is model-
agnostic). Run from the repo root:

    ml/.venv/bin/python -m ml.rag.experiments.run_benchmark

Candidates are built, evaluated, and discarded one at a time (not all held
in VRAM together — see candidates.py) so this fits the 8GB GPU documented
in CLAUDE.md. Writes full per-query rankings to results.json (raw evidence
for scrutiny/reproducibility) and prints an aggregate metrics table. See
RESULTS.md for the write-up and final decision.
"""

import gc
import json
import time
from pathlib import Path

import numpy as np
import torch

from ml.rag.experiments.candidates import CANDIDATE_FACTORIES
from ml.rag.experiments.eval_data import PASSAGES, QUERIES
from ml.rag.experiments.metrics import reciprocal_rank, recall_at_k

OUTPUT_PATH = Path(__file__).resolve().parent / "results.json"


def rank_passages(query_vector: np.ndarray, passage_vectors: np.ndarray, passage_ids: list[str]) -> list[str]:
    """Rank passage ids by cosine similarity (vectors are pre-normalized, so dot product suffices)."""
    scores = passage_vectors @ query_vector
    order = np.argsort(-scores)
    return [passage_ids[i] for i in order]


def evaluate_candidate(candidate) -> dict:
    """Embed the full eval set with one candidate and score it against the relevance judgments."""
    passage_ids = [p["id"] for p in PASSAGES]
    passage_vectors = candidate.embed_passages([p["text"] for p in PASSAGES])
    query_vectors = candidate.embed_queries([q["text"] for q in QUERIES])

    per_query, recall_3, recall_5, recall_10, mrr = [], [], [], [], []
    for query, qvec in zip(QUERIES, query_vectors):
        ranked = rank_passages(qvec, passage_vectors, passage_ids)
        relevant = set(query["relevant_ids"])
        recall_3.append(recall_at_k(ranked, relevant, 3))
        recall_5.append(recall_at_k(ranked, relevant, 5))
        recall_10.append(recall_at_k(ranked, relevant, 10))
        mrr.append(reciprocal_rank(ranked, relevant))
        per_query.append({"query": query["text"], "ranked_top5": ranked[:5], "relevant_ids": sorted(relevant)})

    n = len(QUERIES)
    return {
        "model": candidate.name,
        "recall@3": round(sum(recall_3) / n, 4),
        "recall@5": round(sum(recall_5) / n, 4),
        "recall@10": round(sum(recall_10) / n, 4),
        "mrr": round(sum(mrr) / n, 4),
        "per_query": per_query,
    }


def main() -> None:
    print(f"Eval set: {len(PASSAGES)} passages, {len(QUERIES)} queries, {len(CANDIDATE_FACTORIES)} candidates\n")
    results = []
    for name, build in CANDIDATE_FACTORIES:
        print(f"--- {name} ---")
        start = time.time()
        candidate = build()
        result = evaluate_candidate(candidate)
        results.append(result)
        print(f"  recall@3={result['recall@3']} recall@5={result['recall@5']} "
              f"recall@10={result['recall@10']} mrr={result['mrr']} ({time.time() - start:.1f}s)")

        # Discard the candidate and free GPU memory before loading the next
        # one — see candidates.py's note on the 8GB VRAM budget.
        del candidate
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    OUTPUT_PATH.write_text(json.dumps(results, indent=2))

    print(f"\n{'Model':<45} {'Recall@3':>9} {'Recall@5':>9} {'Recall@10':>10} {'MRR':>7}")
    for r in results:
        print(f"{r['model']:<45} {r['recall@3']:>9} {r['recall@5']:>9} {r['recall@10']:>10} {r['mrr']:>7}")
    print(f"\nFull per-query rankings written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
