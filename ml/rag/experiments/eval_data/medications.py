"""
Medication topics for the embedding-model-selection eval set.

10 topics x 5 clinical-note-style passages, 3 queries each — see
eval_data/__init__.py for combination logic and ../RESULTS.md for
methodology.
"""

TOPICS = {
    "statin": [
        "Atorvastatin 20mg daily started on 2025-11-01 for hyperlipidemia management.",
        "Statin dose increased from atorvastatin 20mg to 40mg on 2026-03-15 due to persistently elevated LDL.",
        "No muscle pain or elevated liver enzymes reported since starting statin therapy.",
        "Patient reports occasional missed doses of atorvastatin, roughly twice per month.",
        "Rosuvastatin considered as an alternative given the patient's mild intolerance to atorvastatin.",
    ],
    "metformin": [
        "Metformin 500mg twice daily started for prediabetes management.",
        "Metformin dose increased to 1000mg twice daily given HbA1c remaining above target.",
        "Patient reports mild gastrointestinal upset with metformin, improved by taking with food.",
        "Metformin held prior to upcoming contrast imaging study per standard protocol.",
        "Renal function confirmed adequate to continue metformin at the current dose.",
    ],
    "insulin": [
        "Long-acting insulin glargine started at 10 units nightly for type 2 diabetes.",
        "Insulin dose titrated up to 18 units nightly based on home glucose logs.",
        "Patient trained on proper insulin injection technique and rotation of injection sites.",
        "Episode of mild hypoglycemia reported after insulin dose increase, dose reduced slightly.",
        "Rapid-acting insulin added at mealtimes given persistently elevated post-meal glucose readings.",
    ],
    "ace_inhibitor": [
        "Lisinopril 10mg daily prescribed for stage 2 hypertension.",
        "Lisinopril dose increased to 20mg daily given blood pressure remaining above goal.",
        "Dry cough reported as a possible side effect of lisinopril, switch to an ARB considered.",
        "Potassium and creatinine checked two weeks after starting lisinopril per standard monitoring.",
        "Blood pressure well controlled on the current lisinopril dose with no reported side effects.",
    ],
    "beta_blocker": [
        "Metoprolol succinate 25mg daily started for rate control and blood pressure management.",
        "Metoprolol dose increased to 50mg daily given persistent tachycardia on recent visits.",
        "Patient reports mild fatigue since starting metoprolol, otherwise tolerating well.",
        "Heart rate well controlled in the 60s on the current beta blocker dose.",
        "Beta blocker continued post-myocardial infarction per standard cardiac protocol.",
    ],
    "levothyroxine": [
        "Levothyroxine 25mcg daily initiated for subclinical hypothyroidism.",
        "Levothyroxine dose increased to 50mcg daily given TSH remaining elevated on repeat testing.",
        "Patient counseled to take levothyroxine on an empty stomach, separate from calcium supplements.",
        "TSH normalized after three months on the current levothyroxine dose.",
        "Levothyroxine dose adjusted slightly downward given mild symptoms of overtreatment.",
    ],
    "anticoagulant_warfarin": [
        "Warfarin started for atrial fibrillation with a goal INR of 2 to 3.",
        "INR measured at 3.8, above therapeutic range, warfarin dose held for one day.",
        "Patient counseled on dietary vitamin K consistency while taking warfarin.",
        "INR stable within therapeutic range on the current warfarin dose for the past three months.",
        "Switch from warfarin to a direct oral anticoagulant discussed given difficulty maintaining stable INR.",
    ],
    "asthma_inhaler": [
        "Albuterol inhaler prescribed as needed for asthma symptom relief.",
        "Inhaled corticosteroid added for daily use given asthma symptoms occurring more than twice weekly.",
        "Patient reports using rescue inhaler about three times per week, more than typical baseline.",
        "Inhaler technique reviewed and corrected during visit to improve medication delivery.",
        "Asthma well controlled on the current combination inhaler with no rescue inhaler use in the past month.",
    ],
    "opioid_pain_management": [
        "Low-dose oxycodone prescribed short-term for acute post-surgical pain.",
        "Opioid tapering plan discussed given a chronic pain patient's long-term use of hydrocodone.",
        "Pain adequately managed on the current opioid regimen with no reported side effects.",
        "Non-opioid alternatives discussed given concerns about long-term opioid use for chronic back pain.",
        "Opioid prescription monitoring program checked prior to renewing pain medication.",
    ],
    "antidepressant_ssri": [
        "Sertraline 50mg daily started for symptoms of depression and anxiety.",
        "Sertraline dose increased to 100mg daily given partial response after six weeks.",
        "Patient reports improved mood and energy since starting SSRI therapy.",
        "Mild nausea reported when starting sertraline, resolved after the first two weeks.",
        "SSRI continued at the current dose given sustained improvement in depression symptoms.",
    ],
}

QUERIES = [
    ("statin", "What statin is the patient taking and at what dose?"),
    ("statin", "Has the cholesterol medication dose changed recently?"),
    ("statin", "Current lipid-lowering medication?"),
    ("metformin", "Is the patient taking metformin?"),
    ("metformin", "What diabetes medication is the patient on?"),
    ("metformin", "Current metformin dose?"),
    ("insulin", "Is the patient on insulin therapy?"),
    ("insulin", "What type of insulin is the patient using?"),
    ("insulin", "Recent insulin dose changes?"),
    ("ace_inhibitor", "Is the patient taking an ACE inhibitor?"),
    ("ace_inhibitor", "What blood pressure medication is the patient on?"),
    ("ace_inhibitor", "Current lisinopril dose?"),
    ("beta_blocker", "Is the patient taking a beta blocker?"),
    ("beta_blocker", "What medication is controlling the patient's heart rate?"),
    ("beta_blocker", "Current metoprolol dose?"),
    ("levothyroxine", "Is the patient on thyroid hormone replacement?"),
    ("levothyroxine", "What medication is the patient taking for hypothyroidism?"),
    ("levothyroxine", "Current levothyroxine dose?"),
    ("anticoagulant_warfarin", "Is the patient on blood thinners?"),
    ("anticoagulant_warfarin", "What anticoagulant is the patient taking?"),
    ("anticoagulant_warfarin", "Recent INR results on warfarin?"),
    ("asthma_inhaler", "What inhaler is the patient using for asthma?"),
    ("asthma_inhaler", "Is the patient's asthma well controlled on current medication?"),
    ("asthma_inhaler", "Rescue inhaler use frequency?"),
    ("opioid_pain_management", "Is the patient on opioid pain medication?"),
    ("opioid_pain_management", "How is the patient's chronic pain being managed?"),
    ("opioid_pain_management", "Current opioid prescription details?"),
    ("antidepressant_ssri", "Is the patient taking an antidepressant?"),
    ("antidepressant_ssri", "What medication is the patient on for depression?"),
    ("antidepressant_ssri", "Current SSRI dose?"),
]
