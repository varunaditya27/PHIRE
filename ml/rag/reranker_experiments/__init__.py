"""
Reranker weight-tuning experiment: does the "patient's own record can
lose to generic reference prose" limitation documented in
ml/rag/reranker.py actually get fixed by re-weighting relevance/
authority/recency, without breaking general-topic query quality?

See RESULTS.md for methodology, results, and the final decision. Run via:
    ml/.venv/bin/python -m ml.rag.reranker_experiments.run_benchmark

Requires the real corpus already ingested this session (public reference
docs via ml/rag/ingest/run_ingest.py, patient documents via
ml/rag/ingest/ingest_patient_document.py) — not a synthetic eval set,
since the whole point is testing against real retrieval competition.
"""
