"""
Chronic condition / history topics for the embedding-model-selection eval
set.

9 topics x 5 clinical-note-style passages, 3 queries each — see
eval_data/__init__.py for combination logic and ../RESULTS.md for
methodology.
"""

TOPICS = {
    "chronic_kidney_disease": [
        "Patient diagnosed with stage 3a chronic kidney disease based on GFR and persistent proteinuria.",
        "Nephrology referral placed given declining kidney function over the past 6 months.",
        "Patient advised to avoid NSAIDs given reduced kidney function.",
        "Chronic kidney disease stable at stage 3a with no significant change over the past year.",
        "Dietary counseling on protein and sodium restriction provided given the chronic kidney disease diagnosis.",
    ],
    "copd": [
        "Patient diagnosed with moderate COPD based on spirometry showing FEV1 of 62% predicted.",
        "COPD exacerbation treated with a short course of oral steroids and antibiotics.",
        "Pulmonary rehabilitation recommended given COPD symptoms limiting daily activity.",
        "Oxygen saturation of 91% on room air noted during COPD follow-up visit.",
        "COPD symptoms well controlled on the current combination inhaler with no recent exacerbations.",
    ],
    "migraine": [
        "Patient reports migraines occurring approximately 4 times per month, each lasting 6 to 8 hours.",
        "Migraine frequency decreased from 8 to 3 per month after starting preventive medication.",
        "Triptan medication prescribed for acute migraine treatment given inadequate response to over-the-counter options.",
        "Migraine triggers identified as poor sleep and skipped meals per the patient's headache diary.",
        "Neurology referral placed given migraines not responding to first-line preventive therapy.",
    ],
    "cardiac_ecg_findings": [
        "ECG shows normal sinus rhythm with no acute ST-segment changes.",
        "ECG reveals atrial fibrillation with a ventricular rate of 110 beats per minute.",
        "Follow-up ECG shows resolution of previously noted ST-segment abnormalities.",
        "First-degree AV block noted on routine ECG, asymptomatic and stable over time.",
        "ECG performed given chest pain shows no evidence of acute ischemia.",
    ],
    "echo_ejection_fraction": [
        "Echocardiogram shows left ventricular ejection fraction of 45%, mildly reduced.",
        "Ejection fraction improved from 35% to 42% after three months of heart failure therapy.",
        "Echocardiogram reveals normal ejection fraction of 60% with no significant valvular abnormalities.",
        "Repeat echocardiogram recommended in 6 months to monitor ejection fraction trend.",
        "Severely reduced ejection fraction of 25% noted, cardiology follow-up scheduled urgently.",
    ],
    "allergy_history": [
        "Patient reports a documented allergy to penicillin causing hives.",
        "No known drug allergies documented in the patient's chart.",
        "Seasonal environmental allergies reported, managed with over-the-counter antihistamines.",
        "Patient reports a severe allergic reaction to shellfish requiring epinephrine in the past.",
        "New allergy to a recently prescribed antibiotic documented after the patient developed a rash.",
    ],
    "family_history": [
        "Family history significant for father with type 2 diabetes diagnosed at age 50.",
        "Strong family history of premature coronary artery disease; mother had a heart attack at age 48.",
        "No significant family history of cancer reported by the patient.",
        "Family history notable for maternal breast cancer, prompting earlier mammogram screening.",
        "Family history of hypertension in both parents documented during intake visit.",
    ],
    "pregnancy_prenatal": [
        "Patient is currently 24 weeks pregnant with an uncomplicated prenatal course to date.",
        "Glucose tolerance test at 26 weeks gestation was within normal limits, ruling out gestational diabetes.",
        "Prenatal ultrasound at 20 weeks shows normal fetal growth and anatomy.",
        "Blood pressure monitored closely given mild elevation noted during third trimester visit.",
        "Prenatal vitamins and folic acid supplementation continued throughout pregnancy per standard care.",
    ],
    "dermatology_skin_lesion": [
        "New pigmented skin lesion on the back noted during annual physical, dermatology referral placed.",
        "Biopsy of suspicious skin lesion confirmed benign seborrheic keratosis.",
        "Patient reports a mole on the arm has changed in size and color over the past few months.",
        "Dermatology follow-up shows stable appearance of a previously biopsied skin lesion.",
        "Skin examination reveals mild eczema on the hands, treated with topical corticosteroid.",
    ],
}

QUERIES = [
    ("chronic_kidney_disease", "Does the patient have chronic kidney disease?"),
    ("chronic_kidney_disease", "What stage is the patient's kidney disease?"),
    ("chronic_kidney_disease", "Latest CKD status?"),
    ("copd", "Does the patient have COPD?"),
    ("copd", "How severe is the patient's lung disease?"),
    ("copd", "Recent spirometry/FEV1 result?"),
    ("migraine", "How often does the patient get migraines?"),
    ("migraine", "Is the patient's headache condition being treated?"),
    ("migraine", "Current migraine management plan?"),
    ("cardiac_ecg_findings", "What did the patient's most recent ECG show?"),
    ("cardiac_ecg_findings", "Does the patient have any heart rhythm abnormalities?"),
    ("cardiac_ecg_findings", "Latest EKG findings?"),
    ("echo_ejection_fraction", "What is the patient's ejection fraction?"),
    ("echo_ejection_fraction", "Does the patient have reduced heart pumping function?"),
    ("echo_ejection_fraction", "Latest echo EF result?"),
    ("allergy_history", "Does the patient have any known drug allergies?"),
    ("allergy_history", "What allergies does the patient have?"),
    ("allergy_history", "Documented NKDA or allergy list?"),
    ("family_history", "What is the patient's family medical history?"),
    ("family_history", "Does the patient have a family history of heart disease?"),
    ("family_history", "Relevant FH for cancer or diabetes?"),
    ("pregnancy_prenatal", "Is the patient currently pregnant?"),
    ("pregnancy_prenatal", "How is the patient's pregnancy progressing?"),
    ("pregnancy_prenatal", "Latest prenatal visit findings?"),
    ("dermatology_skin_lesion", "Does the patient have any concerning skin lesions?"),
    ("dermatology_skin_lesion", "What did the dermatology evaluation find?"),
    ("dermatology_skin_lesion", "Recent skin biopsy result?"),
]
