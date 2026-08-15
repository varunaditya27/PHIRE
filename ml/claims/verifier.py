"""
Claim verification against retrieved evidence.

Responsibilities (to implement):
- For each extracted claim, check NLI-style entailment against evidence
  passages/observations (candidate approach: MedRAGChecker) and assign a
  status: SUPPORTED, DERIVED, INFERRED, UNCERTAIN, CONFLICTING, or
  UNSUPPORTED.
- Unsupported claims must be flagged for removal/abstention, never
  surfaced to the user as fact.
"""
