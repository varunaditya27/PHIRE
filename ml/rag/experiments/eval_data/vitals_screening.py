"""
Vitals and screening topics for the embedding-model-selection eval set.

9 topics x 5 clinical-note-style passages, 3 queries each — see
eval_data/__init__.py for combination logic and ../RESULTS.md for
methodology.
"""

TOPICS = {
    "blood_pressure": [
        "Blood pressure recorded at 148/92 mmHg during clinic visit on 2026-01-20.",
        "Home blood pressure readings over two weeks averaged 142/88 mmHg.",
        "Blood pressure improved to 128/80 mmHg after four weeks on lisinopril.",
        "Orthostatic blood pressure checked given the patient's report of dizziness on standing.",
        "Blood pressure log reviewed showing readings consistently above 140/90 mmHg over the past month.",
    ],
    "bmi_weight": [
        "BMI calculated at 31.2 kg/m2, consistent with obesity class 1.",
        "Weight decreased from 210 to 195 pounds over six months with diet and exercise.",
        "BMI trending upward over the past two years, from 27 to 31 kg/m2.",
        "Weight loss goal of 10% body weight set given BMI and associated health risks.",
        "Weight stable at 165 pounds with a BMI of 23.4, within the normal range.",
    ],
    "depression_anxiety_screening": [
        "PHQ-9 score of 14 indicates moderate depression on today's screening.",
        "GAD-7 score of 9 suggests mild anxiety symptoms.",
        "PHQ-9 score improved from 16 to 8 after three months of SSRI therapy.",
        "Patient screened negative for depression with a PHQ-9 score of 2.",
        "Follow-up mental health screening scheduled given an elevated GAD-7 score on today's visit.",
    ],
    "bone_density_osteoporosis": [
        "DEXA scan shows a T-score of -2.6 at the hip, consistent with osteoporosis.",
        "Bone density improved slightly on repeat DEXA scan after starting calcium and vitamin D.",
        "T-score of -1.8 at the spine indicates osteopenia, below normal bone density.",
        "Bisphosphonate therapy started given an osteoporosis diagnosis on recent bone density scan.",
        "Repeat DEXA scan recommended in two years to monitor bone density trend.",
    ],
    "hearing_vision_screening": [
        "Hearing screening shows mild high-frequency hearing loss in both ears.",
        "Vision screening reveals visual acuity of 20/40 in the right eye, referred to ophthalmology.",
        "Annual hearing test shows no significant change from the prior year's baseline.",
        "Patient reports difficulty hearing in noisy environments, hearing aid evaluation recommended.",
        "Vision corrected to 20/20 with current prescription glasses on today's screening.",
    ],
    "sleep_apnea": [
        "Sleep study shows an apnea-hypopnea index of 22, consistent with moderate sleep apnea.",
        "CPAP therapy started given a moderate obstructive sleep apnea diagnosis.",
        "Patient reports improved daytime energy since starting CPAP for sleep apnea.",
        "Snoring and witnessed pauses in breathing reported by spouse, sleep study ordered.",
        "CPAP compliance data shows average use of 6 hours per night over the past month.",
    ],
    "smoking_status": [
        "Patient reports smoking one pack of cigarettes per day for the past 15 years.",
        "Smoking cessation counseling provided along with nicotine replacement therapy prescription.",
        "Patient successfully quit smoking three months ago using a combination of counseling and medication.",
        "Current smoking status documented as former smoker, quit five years ago.",
        "Patient continues to smoke despite counseling, expresses interest in quitting in the future.",
    ],
    "alcohol_use": [
        "Patient reports drinking approximately 2 to 3 alcoholic beverages per week.",
        "AUDIT-C screening score suggests at-risk alcohol use, brief counseling provided.",
        "Patient reports no alcohol use in the past year.",
        "Alcohol use increased to daily drinking over the past six months per patient report.",
        "Referral to substance use counseling offered given an elevated alcohol screening score.",
    ],
    "immunization_status": [
        "Influenza vaccine administered during today's visit per seasonal recommendation.",
        "Patient is up to date on all recommended vaccinations per immunization record review.",
        "Shingles vaccine series completed with second dose given six months after the first.",
        "Tetanus booster given today, last dose was over 10 years ago.",
        "COVID-19 booster vaccine offered and administered during today's visit.",
    ],
}

QUERIES = [
    ("blood_pressure", "What are the patient's recent blood pressure readings?"),
    ("blood_pressure", "Is the patient's hypertension under control?"),
    ("blood_pressure", "Latest BP reading?"),
    ("bmi_weight", "What is the patient's BMI?"),
    ("bmi_weight", "Has the patient's weight changed recently?"),
    ("bmi_weight", "Current weight and BMI?"),
    ("depression_anxiety_screening", "What was the patient's most recent depression screening result?"),
    ("depression_anxiety_screening", "Does the patient show signs of anxiety?"),
    ("depression_anxiety_screening", "Latest PHQ-9 and GAD-7 scores?"),
    ("bone_density_osteoporosis", "Does the patient have osteoporosis?"),
    ("bone_density_osteoporosis", "What did the bone density scan show?"),
    ("bone_density_osteoporosis", "Latest DEXA T-score?"),
    ("hearing_vision_screening", "Does the patient have any hearing or vision problems?"),
    ("hearing_vision_screening", "What did the recent hearing and vision screening show?"),
    ("hearing_vision_screening", "Latest visual acuity result?"),
    ("sleep_apnea", "Does the patient have sleep apnea?"),
    ("sleep_apnea", "How is the patient's sleep apnea being managed?"),
    ("sleep_apnea", "Recent AHI result from sleep study?"),
    ("smoking_status", "Does the patient smoke?"),
    ("smoking_status", "What is the patient's smoking history?"),
    ("smoking_status", "Current tobacco use status?"),
    ("alcohol_use", "How much alcohol does the patient drink?"),
    ("alcohol_use", "Is the patient's alcohol use a concern?"),
    ("alcohol_use", "Recent AUDIT-C screening result?"),
    ("immunization_status", "Is the patient up to date on vaccinations?"),
    ("immunization_status", "What vaccines has the patient recently received?"),
    ("immunization_status", "Recent immunization record?"),
]
