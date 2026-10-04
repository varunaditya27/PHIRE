"""
Canonical metric names, so "LDL", "LDL Cholesterol", and "LDL cholesterol"
all become the same graph identity instead of three separate Observation
nodes for the same lab test -- see docs/PHIRE_STRUCTURED_GRAPH_MEDICAL_CORPUS_IMPLEMENTATION.md
section 10.

Deterministic lexical matching only, no SLM -- per that doc's own
guidance ("prefer deterministic/lexical matching first"), and per
GRAPH_SCHEMA_ROADMAP.md's discipline of not building more than what's
demonstrated as needed. This alias table is seeded from panels actually
seen in ingested data plus their obvious real-world variants, not a
speculative LOINC-scale terminology -- add an entry when a real document
introduces a metric name not covered here.
"""

# canonical name -> every raw phrasing that should resolve to it (lowercase).
# The canonical name itself does not need to be listed as an alias.
_METRIC_ALIASES: dict[str, list[str]] = {
    "LDL Cholesterol": ["ldl", "ldl-c", "low density lipoprotein", "low-density lipoprotein cholesterol"],
    "HDL Cholesterol": ["hdl", "hdl-c", "high density lipoprotein", "high-density lipoprotein cholesterol"],
    "Total Cholesterol": ["cholesterol, total", "total chol"],
    "Triglycerides": ["trig", "trigs"],
    "Glucose": ["fasting glucose", "blood glucose", "blood sugar"],
    "Sodium": ["na"],
    "Potassium": ["k"],
    "Chloride": ["cl"],
    "CO2": ["carbon dioxide", "bicarbonate"],
    "BUN": ["blood urea nitrogen"],
    "Creatinine": ["creat"],
    "Calcium": ["ca"],
    "Blood Pressure": ["bp"],
    "Heart Rate": ["pulse", "pulse rate", "hr"],
    "Visual Acuity": ["va", "vision", "eyesight"],
    "Height": ["ht", "body height", "stature"],
}

# Reverse index built once at import time: lowercased alias -> canonical name.
_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: canonical for canonical, aliases in _METRIC_ALIASES.items() for alias in aliases
}


def resolve_metric(raw_name: str) -> str:
    """Map a raw extracted metric name to its canonical form, or return it unchanged if unrecognized.

    Matches on the raw name itself (case/whitespace-normalized) against
    both canonical names and aliases -- "LDL cholesterol" and "LDL
    Cholesterol" both resolve to the same canonical form this way, without
    needing every canonical name duplicated into its own alias list. No
    confidence score: this is exact lexical matching, not a fuzzy/semantic
    guess, so there's nothing to threshold -- it either matches or it
    doesn't, and an unmatched name passes through as-is (preserves the
    original rather than forcing a bad mapping).
    """
    normalized = raw_name.strip().lower()
    for canonical in _METRIC_ALIASES:
        if normalized == canonical.lower():
            return canonical
    return _ALIAS_TO_CANONICAL.get(normalized, raw_name)
