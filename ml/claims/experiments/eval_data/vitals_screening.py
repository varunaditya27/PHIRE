"""
Vitals/screening topics' claims (see ml/rag/experiments/eval_data/vitals_screening.py for the matching premises).
"""

CLAIMS: dict[str, dict[str, str]] = {
    "blood_pressure": {
        "entailment": "The patient's blood pressure reading was elevated at this visit.",
        "contradiction": "The patient's blood pressure reading was normal at this visit.",
        "neutral": "The patient's cholesterol panel was drawn during the same visit.",
    },
    "bmi_weight": {
        "entailment": "The patient's BMI falls in the obesity range.",
        "contradiction": "The patient's BMI is in the normal weight range.",
        "neutral": 'The patient was referred to a dietitian for nutrition counseling.',
    },
    "depression_anxiety_screening": {
        "entailment": "The patient's screening score indicates moderate depression.",
        "contradiction": "The patient's screening score indicates no depression symptoms.",
        "neutral": "The patient's blood pressure was also checked at this visit.",
    },
    "bone_density_osteoporosis": {
        "entailment": "The patient's DEXA scan is consistent with osteoporosis.",
        "contradiction": "The patient's bone density is normal for their age.",
        "neutral": 'The patient was advised to take calcium and vitamin D supplements.',
    },
    "hearing_vision_screening": {
        "entailment": 'The patient has mild hearing loss in both ears.',
        "contradiction": "The patient's hearing screening was completely normal.",
        "neutral": "The patient's vision screening is scheduled for next week.",
    },
    "sleep_apnea": {
        "entailment": "The patient's sleep study is consistent with moderate sleep apnea.",
        "contradiction": "The patient's sleep study showed no evidence of sleep apnea.",
        "neutral": 'The patient reports feeling tired most afternoons.',
    },
    "smoking_status": {
        "entailment": 'The patient has a 15-year history of smoking one pack per day.',
        "contradiction": 'The patient has never smoked cigarettes.',
        "neutral": 'The patient was counseled on heart-healthy diet choices.',
    },
    "alcohol_use": {
        "entailment": 'The patient drinks a few alcoholic beverages per week.',
        "contradiction": 'The patient reports drinking alcohol daily.',
        "neutral": "The patient's liver enzymes were within normal limits.",
    },
    "immunization_status": {
        "entailment": "The patient received a flu vaccine at today's visit.",
        "contradiction": "The patient declined the flu vaccine at today's visit.",
        "neutral": "The patient's next physical is scheduled for one year from now.",
    },
}
