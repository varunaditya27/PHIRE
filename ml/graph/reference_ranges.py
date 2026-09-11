"""
Standard clinical reference ranges for common lab markers, used to
compute a derived "is this value normal/high/low" fact the same way
patient_context.py's get_trend_facts precomputes a delta -- arithmetic
comparison against a threshold is exact and deterministic, not something
ml/claims/verifier.py's NLI entailment check can confirm on its own (see
that module's docstring: it can verify a claim restates a sentence, not
that 4.74 < 5.7).

Only used when the source document itself didn't print a reference_range/
interpretation for that observation (see get_reference_range_facts) --
the report's own printed values always take precedence over this table.

Scope is deliberately the labs subset of ml/rag/ingest/topics.py's
CLINICAL_TOPICS, not an exhaustive terminology: these are the same
markers this app already has MedlinePlus/PubMed reference literature
for for. Values are the standard ranges published by MedlinePlus/NIH for
each (the same public source already ingested into the reference
corpus), not a clinical judgment call -- add an entry only when backed by
a citable standard reference range, and prefer omitting a marker over
guessing at one.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReferenceRange:
    unit: str
    # Ascending (exclusive upper bound, label for values below it) pairs.
    # A value strictly less than the first bound gets its label; anything
    # at or above the last bound gets overflow_label. Two bands (one
    # threshold) models a simple low/normal/high range; more bands model
    # a multi-tier range like HbA1c's normal/prediabetes/diabetes.
    bands: tuple[tuple[float, str], ...]
    overflow_label: str
    citation: str  # human-readable summary of the range, for the fact sentence


def classify(value: float, ref: ReferenceRange) -> str:
    for upper_bound, label in ref.bands:
        if value < upper_bound:
            return label
    return ref.overflow_label


# key: normalized metric name (lowercased, spaces/hyphens/underscores
# stripped) -> ReferenceRange. Populated via _register below so each
# marker's real-world name variants can be declared next to its range.
_REFERENCE_RANGES: dict[str, ReferenceRange] = {}


def _normalize(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _register(range_: ReferenceRange, *names: str) -> None:
    for name in names:
        _REFERENCE_RANGES[_normalize(name)] = range_


_register(
    ReferenceRange(
        unit="%", overflow_label="in the diabetes range",
        bands=((5.7, "within the normal range"), (6.5, "in the prediabetes range")),
        citation="below 5.7% normal, 5.7-6.4% prediabetes, 6.5% or above diabetes",
    ),
    "HbA1c", "Hemoglobin A1c", "A1c", "Glycated Hemoglobin",
)
_register(
    ReferenceRange(
        unit="µIU/mL", overflow_label="above the normal range",
        bands=((0.4, "below the normal range"), (4.0, "within the normal range")),
        citation="0.4-4.0 µIU/mL",
    ),
    "TSH", "Thyroid Stimulating Hormone",
)
_register(
    ReferenceRange(
        unit="mg/dL", overflow_label="above the recommended level",
        bands=((100.0, "within the recommended range"),),
        citation="below 100 mg/dL optimal",
    ),
    "LDL Cholesterol",
)
_register(
    ReferenceRange(
        unit="mg/dL", overflow_label="within the healthy range",
        bands=((40.0, "below the healthy range"),),
        citation="40 mg/dL or above healthy (higher is better for HDL)",
    ),
    "HDL Cholesterol",
)
_register(
    ReferenceRange(
        unit="mg/dL", overflow_label="above the normal range",
        bands=((150.0, "within the normal range"),),
        citation="below 150 mg/dL normal",
    ),
    "Triglycerides",
)
_register(
    ReferenceRange(
        unit="mg/dL", overflow_label="in the diabetes range",
        bands=((100.0, "within the normal range"), (126.0, "in the prediabetes range")),
        citation="below 100 mg/dL normal, 100-125 prediabetes, 126 or above diabetes",
    ),
    "Glucose", "Fasting Glucose", "Fasting Blood Glucose", "Blood Glucose",
)
_register(
    ReferenceRange(
        unit="ng/mL", overflow_label="within or above the sufficient range",
        bands=((20.0, "deficient"),),
        citation="20 ng/mL or above sufficient",
    ),
    "Vitamin D", "25-Hydroxyvitamin D",
)
_register(
    ReferenceRange(
        unit="pg/mL", overflow_label="within the normal range",
        bands=((200.0, "below the normal range"),),
        citation="200 pg/mL or above normal",
    ),
    "Vitamin B12",
)
_register(
    ReferenceRange(
        unit="mg/dL", overflow_label="above the normal range",
        bands=((6.0, "within the normal range"),),
        citation="below 6.0 mg/dL normal (varies slightly by sex)",
    ),
    "Uric Acid",
)
_register(
    ReferenceRange(
        unit="mEq/L", overflow_label="above the normal range",
        bands=((3.5, "below the normal range"), (5.0, "within the normal range")),
        citation="3.5-5.0 mEq/L",
    ),
    "Potassium",
)


def get_reference_range(metric_name: str) -> ReferenceRange | None:
    return _REFERENCE_RANGES.get(_normalize(metric_name))


# Health topics a question might name, mapped to the marker names that
# actually answer it -- lets a question like "do I have diabetes" check
# exactly the relevant markers directly instead of relying on an LLM to
# free-associate across a patient's entire (possibly unrelated) panel and
# then have NLI try to verify its guess. Keyword -> topic id mirrors
# ml/rag/ingest/topics.py's CLINICAL_TOPICS ids where they overlap.
TOPIC_MARKERS: dict[str, list[str]] = {
    "diabetes": ["HbA1c", "Glucose"],
    "thyroid": ["TSH", "Free T4"],
    "cholesterol": ["LDL Cholesterol", "HDL Cholesterol", "Triglycerides"],
    "kidney": ["Creatinine"],
    "gout": ["Uric Acid"],
    "vitamin_d": ["Vitamin D"],
    "vitamin_b12": ["Vitamin B12"],
    "electrolytes": ["Potassium"],
}

# question keyword -> topic id. Deliberately simple substring matching
# (see ml/graph/reference_ranges.py's module docstring on scope/style) --
# a full intent classifier is a separate concern (app/services/
# intent_classifier.py); this only needs to catch the common ways someone
# names one of the topics above.
_TOPIC_KEYWORDS: dict[str, str] = {
    "diabetes": "diabetes", "diabetic": "diabetes", "blood sugar": "diabetes",
    "hba1c": "diabetes", "a1c": "diabetes", "prediabetes": "diabetes",
    "thyroid": "thyroid", "hypothyroid": "thyroid", "hyperthyroid": "thyroid", "tsh": "thyroid",
    "cholesterol": "cholesterol", "lipid": "cholesterol",
    "kidney": "kidney", "renal": "kidney", "creatinine": "kidney",
    "gout": "gout", "uric acid": "gout",
    "vitamin d": "vitamin_d",
    "vitamin b12": "vitamin_b12", "b12": "vitamin_b12",
    "potassium": "electrolytes", "electrolyte": "electrolytes",
}


def detect_topic(question: str) -> str | None:
    """Return the topic id a question is asking about, or None if it doesn't name one."""
    q = question.lower()
    for keyword, topic in _TOPIC_KEYWORDS.items():
        if keyword in q:
            return topic
    return None
