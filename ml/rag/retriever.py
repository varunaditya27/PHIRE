"""
Hybrid retrieval over ingested documents + trusted reference sources.

Responsibilities (to implement):
- Combine lexical (BM25, via rank_bm25) and semantic (dense embedding)
  search — BM25 catches exact lab-value/term matches that embeddings can
  miss.
- Vector backend: Chroma, run in-process (not a Docker container).
- Embeddings via Sentence-Transformers (candidates: allenai-specter,
  pubmedbert, msmarco-distilbert-base-v4).
- Returns ranked evidence passages consumed by ml/chains/qa_chain.py.
"""
