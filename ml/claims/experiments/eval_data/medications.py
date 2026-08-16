"""
Medication topics' claims (see ml/rag/experiments/eval_data/medications.py for the matching premises).
"""

CLAIMS: dict[str, dict[str, str]] = {
    "statin": {
        "entailment": 'The patient was started on atorvastatin for high cholesterol.',
        "contradiction": 'The patient was taken off atorvastatin.',
        "neutral": "The patient's next lipid panel is scheduled for six months from now.",
    },
    "metformin": {
        "entailment": 'The patient started taking metformin for prediabetes.',
        "contradiction": 'The patient has never taken metformin.',
        "neutral": 'The patient was encouraged to increase physical activity.',
    },
    "insulin": {
        "entailment": 'The patient started long-acting insulin for type 2 diabetes.',
        "contradiction": "The patient's diabetes is managed without any insulin.",
        "neutral": "The patient's diabetes was diagnosed five years ago.",
    },
    "ace_inhibitor": {
        "entailment": 'The patient was prescribed lisinopril for high blood pressure.',
        "contradiction": 'The patient was not prescribed any blood pressure medication.',
        "neutral": "The patient's cholesterol was also reviewed at this visit.",
    },
    "beta_blocker": {
        "entailment": 'The patient started metoprolol for rate and blood pressure control.',
        "contradiction": 'The patient stopped taking metoprolol.',
        "neutral": "The patient's echocardiogram was scheduled for next month.",
    },
    "levothyroxine": {
        "entailment": 'The patient started levothyroxine for hypothyroidism.',
        "contradiction": "The patient's thyroid hormone levels are being managed without medication.",
        "neutral": "The patient's weight has been stable over the past year.",
    },
    "anticoagulant_warfarin": {
        "entailment": 'The patient started warfarin because of atrial fibrillation.',
        "contradiction": 'The patient is not on any anticoagulation therapy.',
        "neutral": "The patient's heart rate was well controlled during the visit.",
    },
    "asthma_inhaler": {
        "entailment": 'The patient was prescribed albuterol for asthma symptoms.',
        "contradiction": 'The patient has no history of asthma.',
        "neutral": 'The patient works outdoors during pollen season.',
    },
    "opioid_pain_management": {
        "entailment": 'The patient was prescribed oxycodone after surgery.',
        "contradiction": "The patient's pain was managed without any opioid medication.",
        "neutral": "The patient's surgery was completed without complications.",
    },
    "antidepressant_ssri": {
        "entailment": 'The patient started sertraline for depression and anxiety.',
        "contradiction": 'The patient declined any medication for mood symptoms.',
        "neutral": "The patient's sleep schedule has become more consistent.",
    },
}
