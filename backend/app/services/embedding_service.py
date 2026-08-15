"""
Vector store interaction for document/evidence embeddings.

Responsibilities (to implement):
- Embed ingested document chunks and trusted reference passages
  (Sentence-Transformers).
- Write/read vectors to Chroma, run in-process (not a Docker container) —
  used by ml/rag/retriever.py for semantic search.
"""
