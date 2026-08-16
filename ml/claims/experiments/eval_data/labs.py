"""
Lab-result topics' claims (see ml/rag/experiments/eval_data/labs.py for the matching premises).
"""

CLAIMS: dict[str, dict[str, str]] = {
    "ldl_cholesterol": {
        "entailment": "The patient's LDL cholesterol increased compared to six months earlier.",
        "contradiction": "The patient's LDL cholesterol decreased compared to six months earlier.",
        "neutral": 'The patient started a new exercise program to help lower cholesterol.',
    },
    "hdl_cholesterol": {
        "entailment": "The patient's HDL cholesterol is below the recommended threshold for men.",
        "contradiction": "The patient's HDL cholesterol is above the recommended threshold.",
        "neutral": "The patient's LDL cholesterol was also measured on the same visit.",
    },
    "triglycerides": {
        "entailment": "The patient's triglyceride level is above the normal range.",
        "contradiction": "The patient's triglyceride level is within the normal range.",
        "neutral": 'The patient was advised to schedule a follow-up appointment in three months.',
    },
    "fasting_glucose": {
        "entailment": "The patient's fasting glucose result is consistent with prediabetes.",
        "contradiction": "The patient's fasting glucose result is normal.",
        "neutral": 'The patient reported occasional headaches during the visit.',
    },
    "hba1c": {
        "entailment": "The patient's HbA1c increased compared to the previous year.",
        "contradiction": "The patient's HbA1c remained unchanged from the previous year.",
        "neutral": "The patient's blood pressure was also checked during the same visit.",
    },
    "creatinine_gfr": {
        "entailment": "The patient's creatinine level is elevated above their baseline.",
        "contradiction": "The patient's creatinine level is at their normal baseline.",
        "neutral": 'The patient was prescribed a new blood pressure medication last month.',
    },
    "liver_enzymes": {
        "entailment": "The patient's liver enzymes are mildly elevated above normal.",
        "contradiction": "The patient's liver enzymes are within the normal range.",
        "neutral": 'The patient reported no history of alcohol use.',
    },
    "cbc_hemoglobin": {
        "entailment": 'The patient has mild anemia based on their hemoglobin level.',
        "contradiction": "The patient's hemoglobin level is normal.",
        "neutral": "The patient's white blood cell count was also measured.",
    },
    "iron_studies": {
        "entailment": "The patient's ferritin level indicates iron deficiency.",
        "contradiction": "The patient's ferritin level is normal.",
        "neutral": 'The patient was advised to eat more leafy green vegetables.',
    },
    "vitamin_d": {
        "entailment": 'The patient has a vitamin D deficiency.',
        "contradiction": "The patient's vitamin D level is sufficient.",
        "neutral": 'The patient spends most of the day indoors for work.',
    },
    "vitamin_b12": {
        "entailment": "The patient's vitamin B12 level is below normal.",
        "contradiction": "The patient's vitamin B12 level is above normal.",
        "neutral": 'The patient follows a vegetarian diet.',
    },
    "potassium_electrolytes": {
        "entailment": "The patient's potassium level is mildly elevated.",
        "contradiction": "The patient's potassium level is low.",
        "neutral": "The patient's blood pressure was well controlled at this visit.",
    },
    "uric_acid": {
        "entailment": "The patient's uric acid level is elevated.",
        "contradiction": "The patient's uric acid level is normal.",
        "neutral": 'The patient reported joint pain in the past but none currently.',
    },
    "tsh": {
        "entailment": "The patient's TSH level is elevated above normal.",
        "contradiction": "The patient's TSH level is within normal limits.",
        "neutral": 'The patient reported feeling more energetic recently.',
    },
    "free_t4": {
        "entailment": "The patient's free T4 is normal even though TSH is elevated.",
        "contradiction": "Both the patient's free T4 and TSH are elevated.",
        "neutral": 'The patient was referred to endocrinology for a separate concern.',
    },
}
