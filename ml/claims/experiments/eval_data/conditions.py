"""
Condition/history topics' claims (see ml/rag/experiments/eval_data/conditions.py for the matching premises).
"""

CLAIMS: dict[str, dict[str, str]] = {
    "chronic_kidney_disease": {
        "entailment": 'The patient has been diagnosed with stage 3a chronic kidney disease.',
        "contradiction": "The patient's kidney function is completely normal.",
        "neutral": 'The patient was referred to a nephrologist for ongoing care.',
    },
    "copd": {
        "entailment": "The patient's spirometry results are consistent with moderate COPD.",
        "contradiction": "The patient's spirometry results are normal.",
        "neutral": 'The patient was advised to enroll in a pulmonary rehabilitation program.',
    },
    "migraine": {
        "entailment": 'The patient experiences migraines about four times a month.',
        "contradiction": 'The patient reports no history of migraines.',
        "neutral": 'The patient keeps a headache diary to track triggers.',
    },
    "cardiac_ecg_findings": {
        "entailment": "The patient's ECG shows a normal rhythm with no acute changes.",
        "contradiction": "The patient's ECG shows acute ST-segment changes.",
        "neutral": "The patient's chest pain resolved before the ECG was performed.",
    },
    "echo_ejection_fraction": {
        "entailment": "The patient's echocardiogram shows a mildly reduced ejection fraction.",
        "contradiction": "The patient's echocardiogram shows a normal ejection fraction.",
        "neutral": 'The patient was referred to cardiology for further evaluation.',
    },
    "allergy_history": {
        "entailment": 'The patient has a documented penicillin allergy.',
        "contradiction": 'The patient has no known drug allergies.',
        "neutral": 'The patient was prescribed a different class of antibiotic.',
    },
    "family_history": {
        "entailment": "The patient's father has type 2 diabetes.",
        "contradiction": 'The patient has no family history of diabetes.',
        "neutral": "The patient's own blood glucose was checked at this visit.",
    },
    "pregnancy_prenatal": {
        "entailment": 'The patient is currently pregnant with no complications so far.',
        "contradiction": 'The patient is not pregnant.',
        "neutral": "The patient's next prenatal visit is scheduled in two weeks.",
    },
    "dermatology_skin_lesion": {
        "entailment": 'The patient was referred to dermatology for a new pigmented skin lesion.',
        "contradiction": 'No skin abnormalities were found during the physical exam.',
        "neutral": "The patient's annual physical also included routine bloodwork.",
    },
}
