"""
Meal plan generation from nutrition model output + patient dietary
constraints/goals (post-MVP).

Dataset decision (finalized, see docs/DATASETS_AND_GRAPH_RAG.md):
- Recipe/meal text + recipe<->image linking: Recipe1M+ (MIT CSAIL,
  request-gated, non-commercial research/education license). Nutrition
  fields (energy, protein, sugar, fat, saturates, salt) exist only for the
  subset of recipes where unit+quantity were both parsed successfully —
  filter explicitly on non-null nutrition before using a recipe as a macro
  source; the rest have no nutrition row at all, not a zero.
- Every generated macro/calorie figure attached to a meal plan should be
  traceable to USDA FoodData Central (public domain reference DB) so meal
  suggestions carry the same evidence-attribution guarantee as PHIRE's
  medical claims.
"""
