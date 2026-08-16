"""
Reranker weight-tuning benchmark. Run from the repo root (requires the
real corpus already ingested -- ml/rag/ingest/run_ingest.py and
ml/rag/ingest/ingest_patient_document.py):

    ml/.venv/bin/python -m ml.rag.reranker_experiments.run_benchmark

For each weight config in eval_data.WEIGHT_CONFIGS, reranks every query
in eval_data.QUERIES against a wide retrieval candidate pool (matching
qa_chain.py's own max(20, top_k*4) sizing) and scores hit@1/hit@3 per
query category. One embedding model + one retriever instance is reused
across all configs (retrieval doesn't change, only reranking does) --
only the reranker gets rebuilt per config, and even that reuses the same
loaded cross-encoder weights via a fresh Reranker instance per config
(cheap: no model reload, just different instance attributes).
"""

import json
from pathlib import Path

from ml.rag.reranker import Reranker
from ml.rag.reranker_experiments.eval_data import QUERIES, WEIGHT_CONFIGS
from ml.rag.reranker_experiments.metrics import hit_at_1, hit_at_3
from ml.rag.retriever import HybridRetriever

OUTPUT_PATH = Path(__file__).resolve().parent / "results.json"
CANDIDATE_POOL_SIZE = 20
TOP_K = 5


def evaluate_config(retriever: HybridRetriever, reranker: Reranker, config: dict) -> dict:
    """Run one weight config over every eval query and score hit@1/hit@3 per category."""
    reranker.relevance_weight = config["relevance"]
    reranker.authority_weight = config["authority"]
    reranker.recency_weight = config["recency"]

    per_query, category_totals = [], {}
    for item in QUERIES:
        candidates = retriever.retrieve(item["query"], top_k=CANDIDATE_POOL_SIZE)
        ranked = reranker.rerank(item["query"], candidates, top_k=TOP_K)
        sources = [c.metadata.get("source", "unknown") for c in ranked]

        h1, h3 = hit_at_1(sources, item["category"]), hit_at_3(sources, item["category"])
        category_totals.setdefault(item["category"], {"hit1": [], "hit3": []})
        category_totals[item["category"]]["hit1"].append(h1)
        category_totals[item["category"]]["hit3"].append(h3)
        per_query.append({
            "query": item["query"], "category": item["category"],
            "top_sources": sources, "hit@1": h1, "hit@3": h3,
        })

    summary = {}
    for category, hits in category_totals.items():
        summary[f"{category}_hit@1"] = round(sum(hits["hit1"]) / len(hits["hit1"]), 4)
        summary[f"{category}_hit@3"] = round(sum(hits["hit3"]) / len(hits["hit3"]), 4)
    return {"config": config["name"], **summary, "per_query": per_query}


def main() -> None:
    print(f"Eval set: {len(QUERIES)} queries, {len(WEIGHT_CONFIGS)} weight configs\n")
    retriever = HybridRetriever()
    reranker = Reranker()

    results = []
    for config in WEIGHT_CONFIGS:
        print(f"--- {config['name']} ---")
        result = evaluate_config(retriever, reranker, config)
        results.append(result)
        print(f"  patient_fact: hit@1={result.get('patient_fact_hit@1')} hit@3={result.get('patient_fact_hit@3')} | "
              f"general_topic: hit@1={result.get('general_topic_hit@1')} hit@3={result.get('general_topic_hit@3')}")

    OUTPUT_PATH.write_text(json.dumps(results, indent=2))

    print(f"\n{'Config':<40} {'PF hit@1':>9} {'PF hit@3':>9} {'GT hit@1':>9} {'GT hit@3':>9}")
    for r in results:
        print(f"{r['config']:<40} {r.get('patient_fact_hit@1', '-'):>9} {r.get('patient_fact_hit@3', '-'):>9} "
              f"{r.get('general_topic_hit@1', '-'):>9} {r.get('general_topic_hit@3', '-'):>9}")
    print(f"\nFull per-query results written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
