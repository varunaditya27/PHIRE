"""
POST /api/evidence/retrieve, POST /api/evidence/verify — evidence pipeline
endpoints (per CONTRIBUTING.md's endpoint list; not enumerated in
REPO_STRUCTURE.md's illustrative tree but required for the ML integration
contract).

Responsibilities (to implement):
- Thin passthrough into ml/rag/retriever.py (retrieve) and
  ml/claims/verifier.py (verify) — keep business logic in ml/, not here.
"""
