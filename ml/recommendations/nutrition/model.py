"""
Nutrition recommendation model (planned for month 6+, post-MVP).

Dataset decision (finalized, see docs/DATASETS_AND_GRAPH_RAG.md):
- Personalization / outcome layer: CGMacros (open access, CC BY-NC-SA 4.0) —
  meal macros linked to real CGM glucose response + Fitbit activity +
  biomarkers, per participant. This is the primary training data for
  "why this recommendation" personalization, matching PHIRE's
  evidence-attribution design (a logged meal + measured outcome is a
  ready-made evidence pair).
- AI4FoodDB is NOT yet finalized — its 10 sub-datasets (DS1-DS10) look
  promising for cross-modal personalization, but no public source
  publishes a column-level schema for DS3 (Nutrition). Do not write
  ingestion code against it until someone has pulled the actual repo,
  opened the files, and confirmed the fields match what's needed. Treat
  as a candidate pending verification, not a committed source.
- CV food identification / macro estimation feeds this model from
  Nutrition5k (primary, CC BY 4.0, weighed ground truth) — see
  ml/recommendations/nutrition/meal_generator.py — with USDA
  FoodData Central as the nutrient-lookup grounding source for any food
  not directly covered by Nutrition5k.

Responsibilities (to implement):
- Candidate approach: collaborative + content-based filtering over
  CGMacros-derived outcome data.
"""
