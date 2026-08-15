"""
SQLAlchemy ORM models (tables) backing the Pydantic schemas in app/models/.

Responsibilities (to implement):
- Tables: documents, observations, medications, conditions, symptoms,
  evidence_passages, claims — mirroring PHIRE's normalized health
  representation.
- Foreign keys tying claims/observations back to their source document for
  full provenance traceability.
- Relational data only — embeddings live in Chroma (see ml/rag/retriever.py),
  not in these tables.
"""
