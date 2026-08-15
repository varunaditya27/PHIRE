"""
PostgreSQL connection management.

Responsibilities (to implement):
- Create and expose a SQLAlchemy engine/session factory built from
  config.Settings.database_url.
- Connection pooling suitable for an async FastAPI app.
- Relational data only (observations, claims, audit logs) — vector search
  is handled separately by Chroma, run in-process, not through this
  connection. See ml/rag/retriever.py.
"""
