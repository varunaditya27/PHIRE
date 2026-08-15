"""
Temporal normalization of health observations into a patient timeline.

Responsibilities (to implement):
- Merge observations across documents/visits into a chronological,
  per-metric timeline (e.g. LDL over time) to support longitudinal
  reasoning and report-to-report comparison.
- Backs GET /api/patient/{id}/timeline.
"""
