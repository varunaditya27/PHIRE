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


# FDA daily values (21 CFR 101.9), used for the FDA "high" / "good source" nutrient-content claims
# (21 CFR 101.54): high = >= 20% of the daily value, good source = 10-19%. USDA reports Vitamin D in ug.
DAILY_VALUES: dict[str, tuple[str, float]] = {
    "Protein": ("g", 50), "Fiber": ("g", 28), "Calcium": ("mg", 1300), "Iron": ("mg", 18),
    "Potassium": ("mg", 4700), "Vitamin C": ("mg", 90), "Vitamin D": ("ug", 20), "Sodium": ("mg", 2300),
}
HIGH_PERCENT_DV, GOOD_SOURCE_PERCENT_DV = 20, 10
LOW_SODIUM_MG = 140  # FDA "low sodium": <= 140 mg per serving

_OLD_FORMAT_RE = re.compile(r"^(?P<name>.+?) — per 100g: (?P<list>.+?)\. Source: USDA FoodData Central \(fdcId (?P<id>\d+)\)\.$")
_OLD_NUTRIENT_RE = re.compile(r"([A-Z][A-Za-z ]*?) (-?[\d.]+(?:e-?\d+)?) ([A-Za-z]+)")


# Spelled-out units: NLI matches "20 grams" in a claim to "19.8 grams" far better than to "19.8 g"
# (measured: "Salmon contains about 20 grams of protein" 0.65 entailment with "g", 0.93 with "grams").
UNIT_WORDS = {"g": "grams", "mg": "milligrams", "ug": "micrograms", "kcal": "calories"}


def _nutrient_name(label: str) -> str:
    """Lowercase nutrient label for use inside a sentence, keeping the vitamin letter capitalized."""
    return re.sub(r"^vitamin ([a-z])$", lambda m: f"vitamin {m[1].upper()}", label.lower())


def _words(value: float, unit: str) -> str:
    """"19.8", "g" -> "19.8 grams"."""
    return f"{value:g} {UNIT_WORDS.get(unit.lower(), unit)}"


def _content_claims(name: str, nutrients: dict[str, tuple[float, str]]) -> list[str]:
    """FDA-style qualitative sentences ("X is high in protein") derived from the per-100g values."""
    claims = []
    for label, (daily_unit, daily_value) in DAILY_VALUES.items():
        if label not in nutrients or nutrients[label][1].lower() != daily_unit:
            continue
        value, unit = nutrients[label]
        percent = value / daily_value * 100
        nutrient = _nutrient_name(label)
        amount = f"it provides {_words(value, unit)} per 100 grams, {percent:.0f}% of the daily value"
        if label == "Sodium":
            if percent >= HIGH_PERCENT_DV:
                claims.append(f"{name} is high in sodium: {amount}.")
            elif value <= LOW_SODIUM_MG:
                claims.append(f"{name} is low in sodium: it provides {_words(value, unit)} per 100 grams.")
        elif percent >= HIGH_PERCENT_DV:
            claims.append(f"{name} is high in {nutrient}: {amount}.")
        elif percent >= GOOD_SOURCE_PERCENT_DV:
            claims.append(f"{name} is a good source of {nutrient}: {amount}.")
    return claims


def format_food_text(food: dict) -> str:
    """Render a search_foods() result as natural-language evidence sentences.

    The old terse "name — per 100g: Protein 19.8 g, ..." form scored poorly against conversational
    claims (BART-MNLI is trained on sentences, not key-value lists), so valid nutrition claims came
    back UNCERTAIN. Qualitative FDA-style sentences come first, then the raw amounts as one readable
    sentence with spelled-out units.
    """
    name = food["description"]
    nutrients = {}
    for label, text in food["nutrients"].items():
        value, unit = text.split(" ", 1)
        nutrients[label] = (float(value), unit)
    amounts = [
        f"{_words(value, unit)} of {'energy' if label == 'Energy' else _nutrient_name(label)}"
        for label, (value, unit) in nutrients.items()
    ]
    listed = f"{', '.join(amounts[:-1])}, and {amounts[-1]}" if len(amounts) > 1 else amounts[0]
    contains = f"Per 100 grams, {name} contains {listed}."
    return " ".join([*_content_claims(name, nutrients), contains, f"Source: USDA FoodData Central (fdcId {food['fdc_id']})."])


def parse_old_food_text(text: str) -> dict | None:
    """Parse a chunk in the old terse format back into a search_foods()-shaped dict (None if it isn't one).

    Lets the stored corpus be upgraded in place without re-querying USDA (whose DEMO_KEY is rate limited).
    """
    match = _OLD_FORMAT_RE.match(text)
    if not match:
        return None
    nutrients = {label.strip(): f"{value} {unit}" for label, value, unit in _OLD_NUTRIENT_RE.findall(match["list"])}
    return {"fdc_id": match["id"], "description": match["name"], "nutrients": nutrients} if nutrients else None
