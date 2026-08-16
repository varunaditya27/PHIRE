"""
USDA FoodData Central ingestion (docs/DATASETS_AND_GRAPH_RAG.md section 2.3:
"ingest into ml/rag/ as an evidence source independent of any recommendation
model training").

Restricted to Foundation/SR Legacy data types: their nutrient values are
lab-analyzed per 100g, unlike "Branded" entries (manufacturer-submitted,
per-serving, one row per UPC — noisy and not what a claim should cite).

Uses the free DEMO_KEY by default. NCBI's eutils and MedlinePlus have no
comparable restriction, but USDA's DEMO_KEY is capped (documented as
~30-1000 requests/hour depending on endpoint) — set USDA_API_KEY (free
registration at api.data.gov) before ingesting more than topics.py's
default food list.
"""

import os
import re
import time

import requests

FDC_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
REQUEST_DELAY_SECONDS = 1.0
_API_KEY = os.environ.get("USDA_API_KEY", "DEMO_KEY")

# Canonical label -> USDA nutrientName(s) that report it (names vary
# slightly across dataset revisions, hence the alias sets).
NUTRIENT_ALIASES: dict[str, set[str]] = {
    "Energy": {"Energy"},
    "Protein": {"Protein"},
    "Fat": {"Total lipid (fat)"},
    "Carbohydrates": {"Carbohydrate, by difference"},
    "Fiber": {"Fiber, total dietary"},
    "Sugars": {"Sugars, total including NLEA", "Sugars, total"},
    "Calcium": {"Calcium, Ca"},
    "Iron": {"Iron, Fe"},
    "Sodium": {"Sodium, Na"},
    "Potassium": {"Potassium, K"},
    "Vitamin C": {"Vitamin C, total ascorbic acid"},
    "Vitamin D": {"Vitamin D (D2 + D3)"},
}


def _extract_nutrients(food_nutrients: list[dict]) -> dict[str, str]:
    """Pick out KEY_NUTRIENTS from USDA's full per-food nutrient list, as "value unit" strings."""
    extracted = {}
    for label, aliases in NUTRIENT_ALIASES.items():
        for nutrient in food_nutrients:
            if nutrient.get("nutrientName") not in aliases:
                continue
            if label == "Energy" and nutrient.get("unitName") != "KCAL":
                continue
            extracted[label] = f"{nutrient['value']:g} {nutrient['unitName'].lower()}"
            break
    return extracted


def _core_term(text: str) -> str:
    """The ingredient name USDA puts before the first comma, e.g. "Apples, raw, with skin" -> "apples"."""
    return text.split(",")[0].strip().lower()


def _closeness_key(description: str, query: str) -> tuple[int, int]:
    """Rank a food description against the query: exact core-term match first, then shortest (most generic).

    USDA's own relevance ranking surfaces composite dishes (e.g.
    "Croissants, apple") above the plain ingredient for a query like
    "apple, raw", and a naive substring check makes it worse — "apple" is
    a substring of "Rose-apples", so it'd rank ahead of the correctly
    pluralized "Apples, raw, with skin". Comparing core terms (the part
    before the first comma, singular/plural-normalized) avoids both.
    """
    query_core = _core_term(query)
    description_core = _core_term(description)
    if description_core in (query_core, f"{query_core}s") or f"{description_core}s" == query_core:
        tier = 0
    elif re.search(rf"\b{re.escape(query_core)}\b", description.lower()):
        tier = 1
    else:
        tier = 2
    return (tier, len(description))


def search_foods(query: str, max_results: int = 3) -> list[dict]:
    """Search Foundation/SR Legacy foods matching query; each result carries per-100g key nutrients."""
    response = requests.get(
        FDC_SEARCH_URL,
        params={
            "query": query,
            "dataType": "Foundation,SR Legacy",
            "pageSize": max(10, max_results),
            "api_key": _API_KEY,
        },
        timeout=15,
    )
    response.raise_for_status()
    time.sleep(REQUEST_DELAY_SECONDS)

    candidates = sorted(
        response.json().get("foods", []),
        key=lambda food: _closeness_key(food["description"], query),
    )

    results = []
    for food in candidates:
        if len(results) >= max_results:
            break
        nutrients = _extract_nutrients(food.get("foodNutrients", []))
        if not nutrients:
            continue
        results.append({
            "fdc_id": food["fdcId"],
            "description": food["description"],
            "published_date": food.get("publishedDate"),
            "nutrients": nutrients,
        })
    return results


def format_food_text(food: dict) -> str:
    """Render a search_foods() result as a retrievable evidence passage."""
    nutrient_list = ", ".join(f"{label} {value}" for label, value in food["nutrients"].items())
    return f"{food['description']} — per 100g: {nutrient_list}. Source: USDA FoodData Central (fdcId {food['fdc_id']})."
