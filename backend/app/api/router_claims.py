"""
POST /api/claims/extract — claim extraction endpoint (per CONTRIBUTING.md's
endpoint list).

Responsibilities (to implement):
- Thin passthrough into ml/claims/extractor.py.
- Typically called internally by router_chat.py's pipeline rather than
  directly by the frontend, but exposed standalone for debugging/evaluation.
"""
