"""
Retrieval hints: which lab metrics a medication or condition is followed through.

The graph stores medications, conditions and observations as separate nodes with no edges between
them, so "how is my statin working?" cannot be answered by looking up a medication node alone. This
small curated table supplies the missing hop at query time -- statin -> LDL, diabetes -> HbA1c.

These are retrieval routing hints (which readings to pull next to each other), NOT medical
assertions: the chat pipeline still verifies every claim against the actual records. Keep it small
and conventional; add an entry only when a real question needs it.
"""

LIPIDS = ["LDL Cholesterol", "Total Cholesterol", "Triglycerides", "HDL Cholesterol"]
GLYCAEMIC = ["HbA1c", "Glucose"]
BLOOD_PRESSURE = ["Blood Pressure", "Blood Pressure (Systolic)", "Blood Pressure (Diastolic)"]

# Drug class word (as a user might say it) -> member drug names (lowercase).
MEDICATION_CLASSES: dict[str, list[str]] = {
    "statin": ["atorvastatin", "rosuvastatin", "simvastatin", "pravastatin", "lovastatin", "pitavastatin"],
    "ace inhibitor": ["lisinopril", "enalapril", "ramipril", "perindopril"],
    "beta blocker": ["metoprolol", "atenolol", "bisoprolol", "propranolol", "carvedilol"],
    "diabetes medication": ["metformin", "glimepiride", "gliclazide", "sitagliptin", "empagliflozin", "dapagliflozin", "insulin"],
    "blood pressure medication": ["lisinopril", "enalapril", "ramipril", "perindopril", "losartan", "telmisartan",
                                  "amlodipine", "metoprolol", "atenolol", "bisoprolol", "hydrochlorothiazide"],
}

# Medication name (lowercase, matched as a substring of the stored code) -> metrics it is followed through.
MEDICATION_METRICS: dict[str, list[str]] = {
    **{name: LIPIDS for name in MEDICATION_CLASSES["statin"] + ["ezetimibe", "fenofibrate"]},
    **{name: GLYCAEMIC for name in MEDICATION_CLASSES["diabetes medication"]},
    **{name: BLOOD_PRESSURE for name in ["lisinopril", "enalapril", "ramipril", "perindopril", "losartan",
                                         "telmisartan", "amlodipine", "hydrochlorothiazide"]},
    **{name: BLOOD_PRESSURE + ["Heart Rate"] for name in MEDICATION_CLASSES["beta blocker"]},
    "levothyroxine": ["TSH"],
}

# Condition keyword (lowercase, matched as a substring of the stored code) -> metrics it is followed through.
CONDITION_METRICS: dict[str, list[str]] = {
    "cholesterol": LIPIDS, "lipidemia": LIPIDS, "dyslipidemia": LIPIDS,
    "diabetes": GLYCAEMIC, "prediabetes": GLYCAEMIC, "glucose": GLYCAEMIC,
    "hypertension": BLOOD_PRESSURE, "blood pressure": BLOOD_PRESSURE,
    "hypothyroid": ["TSH"], "anemia": ["Hemoglobin"], "kidney": ["Creatinine", "eGFR"],
}


def metrics_for_medication(code: str) -> list[str]:
    """Metrics a medication is followed through (empty if the drug is not in the table)."""
    lowered = code.lower()
    return next((metrics for name, metrics in MEDICATION_METRICS.items() if name in lowered), [])


def metrics_for_condition(code: str) -> list[str]:
    """Metrics a condition is followed through (empty if no keyword matches)."""
    lowered = code.lower()
    return next((metrics for keyword, metrics in CONDITION_METRICS.items() if keyword in lowered), [])


def medications_in_class(phrase: str) -> list[str]:
    """Drug names for a class phrase found in `phrase` ("statin" -> atorvastatin, ...)."""
    lowered = phrase.lower()
    return [drug for cls, drugs in MEDICATION_CLASSES.items() if cls in lowered for drug in drugs]
