"""
Clinical topics and food queries that seed the ingestion pipeline.

CLINICAL_TOPICS reuses the 43 topic ids from ml/rag/experiments/eval_data
(labs, medications, vitals/screening, conditions) rather than inventing a
separate list — that set was already validated as a representative spread
of what PHIRE's RAG layer needs to answer, so ingestion targets the same
ground truth the embedding-model benchmark was scored against. Each id
maps to a natural-language query string for PubMed/MedlinePlus search.

FOOD_QUERIES is a curated set of common whole foods for USDA FoodData
Central ingestion — deliberately not exhaustive (USDA's DEMO_KEY rate
limit makes a bulk pull impractical; see usda.py), chosen to cover the
food groups a nutrition claim is most likely to reference.
"""

CLINICAL_TOPICS: dict[str, str] = {
    "ldl_cholesterol": "LDL cholesterol",
    "hdl_cholesterol": "HDL cholesterol",
    "triglycerides": "triglycerides blood test",
    "fasting_glucose": "fasting blood glucose",
    "hba1c": "HbA1c hemoglobin A1c test",
    "creatinine_gfr": "creatinine and GFR kidney function test",
    "liver_enzymes": "liver enzymes ALT AST blood test",
    "cbc_hemoglobin": "complete blood count hemoglobin",
    "potassium_electrolytes": "potassium and electrolyte blood test",
    "tsh": "TSH thyroid stimulating hormone test",
    "free_t4": "free T4 thyroid hormone test",
    "vitamin_d": "vitamin D blood test deficiency",
    "vitamin_b12": "vitamin B12 deficiency test",
    "iron_studies": "iron deficiency anemia iron studies",
    "uric_acid": "uric acid blood test gout",
    "statin": "statin medication cholesterol",
    "metformin": "metformin diabetes medication",
    "insulin": "insulin therapy diabetes",
    "levothyroxine": "levothyroxine thyroid medication",
    "ace_inhibitor": "ACE inhibitor blood pressure medication",
    "beta_blocker": "beta blocker medication heart",
    "anticoagulant_warfarin": "warfarin anticoagulant medication",
    "antidepressant_ssri": "SSRI antidepressant medication",
    "asthma_inhaler": "asthma inhaler medication",
    "opioid_pain_management": "opioid pain management medication safety",
    "blood_pressure": "blood pressure hypertension measurement",
    "bmi_weight": "body mass index BMI weight",
    "bone_density_osteoporosis": "bone density osteoporosis screening",
    "cardiac_ecg_findings": "ECG electrocardiogram findings",
    "echo_ejection_fraction": "echocardiogram ejection fraction heart",
    "hearing_vision_screening": "hearing and vision screening",
    "depression_anxiety_screening": "depression and anxiety screening",
    "immunization_status": "adult immunization vaccine schedule",
    "smoking_status": "smoking cessation health risk",
    "alcohol_use": "alcohol use health risk screening",
    "family_history": "family history genetic health risk",
    "allergy_history": "drug and food allergy history",
    "pregnancy_prenatal": "prenatal care pregnancy screening",
    "chronic_kidney_disease": "chronic kidney disease",
    "copd": "chronic obstructive pulmonary disease COPD",
    "migraine": "migraine headache treatment",
    "sleep_apnea": "obstructive sleep apnea",
    "dermatology_skin_lesion": "skin lesion dermatology screening",
}

# Deliberately phrased close to USDA's own description style ("apple,
# raw" not "apple") — a bare ingredient name ranks composite dishes
# ("Croissants, apple") above the raw ingredient, which is the wrong
# evidence for a plain nutrition claim.
FOOD_QUERIES: list[str] = [
    "apple, raw", "banana, raw", "orange, raw", "strawberries, raw",
    "blueberries, raw", "avocado, raw", "spinach, raw", "broccoli, raw",
    "carrots, raw", "sweet potato, raw", "kale, raw", "tomato, raw",
    "rice, brown, cooked", "rice, white, cooked", "oats, raw",
    "quinoa, cooked", "bread, whole wheat", "chicken breast, cooked",
    "salmon, cooked", "tuna, canned", "egg, whole, cooked",
    "beef, ground, cooked", "turkey, cooked", "tofu, raw",
    "beans, black, cooked", "chickpeas, cooked", "lentils, cooked",
    "almonds", "walnuts", "peanut butter", "yogurt, greek",
    "milk, whole", "cheese, cheddar", "oil, olive", "butter",
    "milk, skim", "orange juice", "coffee", "tea", "potato, raw",
    "corn, sweet, raw", "green beans, raw", "cucumber, raw",
    "peppers, sweet, raw", "onions, raw", "garlic, raw", "pasta, cooked",
    "cereal", "granola", "honey", "sugar, granulated",
]
