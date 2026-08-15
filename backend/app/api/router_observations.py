"""
GET /api/patient/{id}/observations — structured health data endpoints.

Responsibilities (to implement):
- Serve normalized observations (labs, medications, conditions, symptoms)
  for a patient, filterable by type and date range.
- This is the endpoint the ML layer's RAG pipeline (ml/rag) reads
  structured context from — keep the response shape stable.
"""
