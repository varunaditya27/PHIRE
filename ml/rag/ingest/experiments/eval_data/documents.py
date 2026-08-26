"""
OCR eval set: 6 synthetic patient documents spanning the layout variety
real records actually have — grid tables (lab panels, vaccine records),
a two-column demographics block, dense narrative prose (progress note,
radiology report), and a mixed prose+list discharge summary. Each uses a
different font (sans/serif/mono) matching how real documents from
different sources look different. Rendered as a clean image and a
degraded "phone photo" variant (perspective warp, blur, noise, vignette,
JPEG compression) by generate_images.py.

Each doc's `sections` describes its layout for the renderer (see
generate_images.py); `ground_truth` is a plain-text linearization used for
CER/WER — note that olmOCR's prompt asks for HTML tables, so CER/WER on
table documents measures rough content overlap, not exact format
fidelity. `key_fields` (format-agnostic substring matching, see
../metrics.py) is the metric that actually matters for table documents.
"""

from pathlib import Path

IMAGES_DIR = Path(__file__).resolve().parent / "images"

DOCUMENTS = [
    {
        "id": "cmp_table",
        "font": "sans",
        "sections": [
            {"type": "text", "lines": [
                "Riverside Medical Group - Comprehensive Metabolic Panel",
                "Patient: R. Thompson        Date of Service: 2026-03-01",
            ]},
            {"type": "table", "headers": ["Test", "Result", "Reference Range", "Flag"], "rows": [
                ["Sodium", "138 mEq/L", "136-145", "Normal"],
                ["Potassium", "5.4 mEq/L", "3.5-5.0", "High"],
                ["Chloride", "101 mEq/L", "98-107", "Normal"],
                ["CO2", "24 mEq/L", "23-29", "Normal"],
                ["BUN", "22 mg/dL", "7-20", "High"],
                ["Creatinine", "1.3 mg/dL", "0.6-1.2", "High"],
                ["Glucose", "118 mg/dL", "70-99", "High"],
                ["Calcium", "9.1 mg/dL", "8.5-10.2", "Normal"],
            ]},
        ],
        "ground_truth": (
            "Riverside Medical Group - Comprehensive Metabolic Panel\n"
            "Patient: R. Thompson        Date of Service: 2026-03-01\n"
            "Test Result Reference Range Flag\n"
            "Sodium 138 mEq/L 136-145 Normal\n"
            "Potassium 5.4 mEq/L 3.5-5.0 High\n"
            "Chloride 101 mEq/L 98-107 Normal\n"
            "CO2 24 mEq/L 23-29 Normal\n"
            "BUN 22 mg/dL 7-20 High\n"
            "Creatinine 1.3 mg/dL 0.6-1.2 High\n"
            "Glucose 118 mg/dL 70-99 High\n"
            "Calcium 9.1 mg/dL 8.5-10.2 Normal"
        ),
        "key_fields": {"Potassium": "5.4 mEq/L", "Creatinine": "1.3 mg/dL", "Glucose": "118 mg/dL"},
    },
    {
        "id": "vaccine_record",
        "font": "sans",
        "sections": [
            {"type": "text", "lines": [
                "Riverside Medical Group - Immunization Record",
                "Patient: R. Thompson        Printed: 2026-03-01",
            ]},
            {"type": "table", "headers": ["Vaccine", "Date", "Lot #", "Site"], "rows": [
                ["Influenza", "2025-10-12", "AB1234", "Left deltoid"],
                ["Tdap", "2024-06-03", "CD5678", "Right deltoid"],
                ["COVID-19 (bivalent)", "2025-01-15", "EF9012", "Left deltoid"],
                ["Shingrix dose 2", "2025-09-20", "GH3456", "Right deltoid"],
            ]},
        ],
        "ground_truth": (
            "Riverside Medical Group - Immunization Record\n"
            "Patient: R. Thompson        Printed: 2026-03-01\n"
            "Vaccine Date Lot # Site\n"
            "Influenza 2025-10-12 AB1234 Left deltoid\n"
            "Tdap 2024-06-03 CD5678 Right deltoid\n"
            "COVID-19 (bivalent) 2025-01-15 EF9012 Left deltoid\n"
            "Shingrix dose 2 2025-09-20 GH3456 Right deltoid"
        ),
        "key_fields": {"Influenza": "2025-10-12", "Shingrix dose 2": "2025-09-20"},
    },
    {
        "id": "demographics_vitals",
        "font": "sans",
        "sections": [
            {"type": "text", "lines": ["Riverside Medical Group - Visit Summary"]},
            {"type": "columns", "left": [
                "Name: R. Thompson", "DOB: 1978-04-22", "Sex: F",
            ], "right": [
                "MRN: 00482913", "Insurance: BlueShield PPO", "Visit Date: 2026-03-01",
            ]},
            {"type": "table", "headers": ["Vital", "Value"], "rows": [
                ["Blood Pressure", "142/91 mmHg"],
                ["Heart Rate", "88 bpm"],
                ["Temperature", "98.9 F"],
                ["SpO2", "97 %"],
                ["BMI", "31.8 kg/m2"],
            ]},
        ],
        "ground_truth": (
            "Riverside Medical Group - Visit Summary\n"
            "Name: R. Thompson        MRN: 00482913\n"
            "DOB: 1978-04-22        Insurance: BlueShield PPO\n"
            "Sex: F        Visit Date: 2026-03-01\n"
            "Vital Value\n"
            "Blood Pressure 142/91 mmHg\n"
            "Heart Rate 88 bpm\n"
            "Temperature 98.9 F\n"
            "SpO2 97 %\n"
            "BMI 31.8 kg/m2"
        ),
        "key_fields": {"MRN": "00482913", "Blood Pressure": "142/91 mmHg", "BMI": "31.8"},
    },
    {
        "id": "progress_note",
        "font": "serif",
        "sections": [
            {"type": "text", "lines": [
                "Riverside Medical Group - Office Visit Note",
                "Patient: R. Thompson        Date: 2026-03-01",
                "",
                "Patient is a 54-year-old presenting for follow-up of",
                "hypertension and hyperlipidemia. Blood pressure remains",
                "elevated at today's visit despite adherence to the current",
                "antihypertensive regimen. Lipid panel from last month showed",
                "persistent elevation in LDL cholesterol at 191 mg/dL.",
                "",
                "Plan: increase lisinopril to 20mg daily, add atorvastatin",
                "40mg at bedtime, recheck basic metabolic panel and lipid",
                "panel in 6 weeks. Patient counseled extensively on dietary",
                "sodium restriction and the importance of medication",
                "adherence.",
            ]},
        ],
        "ground_truth": (
            "Riverside Medical Group - Office Visit Note\n"
            "Patient: R. Thompson        Date: 2026-03-01\n"
            "\n"
            "Patient is a 54-year-old presenting for follow-up of "
            "hypertension and hyperlipidemia. Blood pressure remains "
            "elevated at today's visit despite adherence to the current "
            "antihypertensive regimen. Lipid panel from last month showed "
            "persistent elevation in LDL cholesterol at 191 mg/dL.\n"
            "\n"
            "Plan: increase lisinopril to 20mg daily, add atorvastatin "
            "40mg at bedtime, recheck basic metabolic panel and lipid "
            "panel in 6 weeks. Patient counseled extensively on dietary "
            "sodium restriction and the importance of medication "
            "adherence."
        ),
        "key_fields": {"LDL cholesterol": "191 mg/dL", "lisinopril": "20mg", "atorvastatin": "40mg"},
    },
    {
        "id": "radiology_report",
        "font": "serif",
        "sections": [
            {"type": "text", "lines": [
                "Riverside Medical Group - Radiology Report",
                "CHEST X-RAY, PA AND LATERAL VIEWS",
                "Patient: R. Thompson        Date: 2026-02-20",
                "",
                "CLINICAL HISTORY: Cough and shortness of breath.",
                "",
                "FINDINGS: The lungs are clear without focal consolidation,",
                "effusion, or pneumothorax. Cardiomediastinal silhouette is",
                "within normal limits. Cardiothoracic ratio measured at",
                "0.48, within normal limits. No acute osseous abnormality.",
                "",
                "IMPRESSION: No acute cardiopulmonary process.",
            ]},
        ],
        "ground_truth": (
            "Riverside Medical Group - Radiology Report\n"
            "CHEST X-RAY, PA AND LATERAL VIEWS\n"
            "Patient: R. Thompson        Date: 2026-02-20\n"
            "\n"
            "CLINICAL HISTORY: Cough and shortness of breath.\n"
            "\n"
            "FINDINGS: The lungs are clear without focal consolidation, "
            "effusion, or pneumothorax. Cardiomediastinal silhouette is "
            "within normal limits. Cardiothoracic ratio measured at 0.48, "
            "within normal limits. No acute osseous abnormality.\n"
            "\n"
            "IMPRESSION: No acute cardiopulmonary process."
        ),
        "key_fields": {"Cardiothoracic ratio": "0.48"},
    },
    {
        "id": "medication_reconciliation",
        "font": "mono",
        "sections": [
            {"type": "text", "lines": [
                "Medication Reconciliation - Discharge",
                "Patient: R. Thompson        Discharge Date: 2026-03-05",
                "",
                "Continue home medications:",
                "- Atorvastatin 40mg nightly",
                "- Lisinopril 20mg daily",
                "- Metformin 1000mg twice daily",
                "",
                "New medications started this admission:",
                "- Apixaban 5mg twice daily for new atrial fibrillation",
                "",
                "Discontinued:",
                "- Aspirin 81mg daily (discontinued due to apixaban initiation)",
                "",
                "Follow up with cardiology in 2 weeks.",
            ]},
        ],
        "ground_truth": (
            "Medication Reconciliation - Discharge\n"
            "Patient: R. Thompson        Discharge Date: 2026-03-05\n"
            "\n"
            "Continue home medications:\n"
            "- Atorvastatin 40mg nightly\n"
            "- Lisinopril 20mg daily\n"
            "- Metformin 1000mg twice daily\n"
            "\n"
            "New medications started this admission:\n"
            "- Apixaban 5mg twice daily for new atrial fibrillation\n"
            "\n"
            "Discontinued:\n"
            "- Aspirin 81mg daily (discontinued due to apixaban initiation)\n"
            "\n"
            "Follow up with cardiology in 2 weeks."
        ),
        "key_fields": {"Apixaban": "5mg", "Metformin": "1000mg", "Aspirin": "81mg"},
    },
]

# clean variant is a lossless render (simulates a direct PDF/scan);
# photo variant is JPEG (simulates an actual phone-camera photo, both in
# format and in the compression artifacts that come with one).
_VARIANT_EXTENSIONS = {"clean": "png", "photo": "jpg"}


def image_pairs() -> list[dict]:
    """Expand DOCUMENTS into one eval item per (document, clean/photo) image."""
    items = []
    for doc in DOCUMENTS:
        for variant, ext in _VARIANT_EXTENSIONS.items():
            items.append({
                "id": f"{doc['id']}_{variant}",
                "document_id": doc["id"],
                "variant": variant,
                "image_path": IMAGES_DIR / f"{doc['id']}_{variant}.{ext}",
                "ground_truth": doc["ground_truth"],
                "key_fields": doc["key_fields"],
            })
    return items
