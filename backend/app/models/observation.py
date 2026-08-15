"""
Pydantic schemas for normalized health observations.

Responsibilities (to implement):
- Observation: value, unit, date, reference range, source document,
  confidence. Medication, Condition, Symptom variants as needed.
- These schemas are the contract behind GET /api/patient/{id}/observations
  and GET /api/patient/{id}/timeline, and feed the ML layer's structured
  retrieval.
"""
