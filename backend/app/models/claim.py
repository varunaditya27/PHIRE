"""
Pydantic schemas for generated claims and their evidence status.

Responsibilities (to implement):
- Claim: generated statement, linked evidence passages/observations, and a
  status in {SUPPORTED, DERIVED, INFERRED, UNCERTAIN, CONFLICTING,
  UNSUPPORTED}.
- This is the core data structure behind PHIRE's claim-level provenance,
  produced by ml/claims/verifier.py.
"""
