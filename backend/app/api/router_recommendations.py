"""
GET /api/recommendations/fitness, GET /api/recommendations/nutrition —
recommendation endpoints (per CONTRIBUTING.md's endpoint list).

fitness: backed by ml/recommendations/fitness (MVP, PAMAP2-based HAR
model). nutrition: backed by ml/recommendations/nutrition (post-MVP,
month 6+ — stub only for now). Returns 501 until those modules expose a
`recommend()` function.
"""

import importlib

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _call_recommend(module_path: str) -> dict:
    try:
        module = importlib.import_module(module_path)
    except ImportError:
        module = None

    recommend_fn = getattr(module, "recommend", None) if module else None
    if recommend_fn is None:
        raise HTTPException(status_code=501, detail=f"{module_path} not implemented yet")

    return recommend_fn()


@router.get("/fitness")
def fitness_recommendations() -> dict:
    return _call_recommend("ml.recommendations.fitness.recommendations")


@router.get("/nutrition")
def nutrition_recommendations() -> dict:
    return _call_recommend("ml.recommendations.nutrition.meal_generator")
