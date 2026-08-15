"""
GET /api/search/* — evidence/document search endpoints.

Responsibilities (to implement):
- Expose hybrid (lexical + semantic) search over ingested documents and
  trusted reference sources, backed by ml/rag/retriever.py.
- Used by the frontend's evidence-display components to resolve citations
  back to exact source passages.
"""
