"""
Eval set for the prose-extraction benchmark: real olmOCR output (not
hand-typed text) for the three prose/mixed documents from
ml/rag/ingest/experiments' OCR benchmark — including the OCR's own minor
noise (e.g. "Cardiome diastinal" for "Cardiomediastinal"), since that's
what extraction actually has to work with in the real pipeline.

medication_reconciliation deliberately exercises "continued" vs "started"
vs "discontinued" medications in one document — the clinically meaningful
distinction a naive extractor might miss, not just name/dosage recall.
"""

DOCUMENTS = [
    {
        "id": "progress_note",
        "text": (
            "Riverside Medical Group - Office Visit Note\nPatient: R. Thompson      Date: 2026-03-01\n\n"
            "Patient is a 54-year-old presenting for follow-up of hypertension and hyperlipidemia. "
            "Blood pressure remains elevated at today's visit despite adherence to the current "
            "antihypertensive regimen. Lipid panel from last month showed persistent elevation in "
            "LDL cholesterol at 191 mg/dL.\n\nPlan: increase lisinopril to 20mg daily, add atorvastatin "
            "40mg at bedtime, recheck basic metabolic panel and lipid panel in 6 weeks. Patient counseled "
            "extensively on dietary sodium restriction and the importance of medication adherence."
        ),
        "medications": [
            {"name": "lisinopril", "dosage": "20mg", "frequency": "daily", "status": "started"},
            {"name": "atorvastatin", "dosage": "40mg", "frequency": "at bedtime", "status": "started"},
        ],
        "observations": [
            {"name": "LDL cholesterol", "value": "191 mg/dL"},
        ],
    },
    {
        "id": "radiology_report",
        "text": (
            "Riverside Medical Group - Radiology Report\nCHEST X-RAY, PA AND LATERAL VIEWS\n"
            "Patient: R. Thompson    Date: 2026-02-20\n\nCLINICAL HISTORY: Cough and shortness of breath.\n\n"
            "FINDINGS: The lungs are clear without focal consolidation, effusion, or pneumothorax. "
            "Cardiome diastinal silhouette is within normal limits. Cardiothoracic ratio measured at 0.48, "
            "within normal limits. No acute osseous abnormality.\n\nIMPRESSION: No acute cardiopulmonary process."
        ),
        "medications": [],
        "observations": [
            {"name": "Cardiothoracic ratio", "value": "0.48"},
        ],
    },
    {
        "id": "medication_reconciliation",
        "text": (
            "Medication Reconciliation - Discharge\nPatient: R. Thompson        Discharge Date: 2026-03-05\n\n"
            "Continue home medications:\n- Atorvastatin 40mg nightly\n- Lisinopril 20mg daily\n"
            "- Metformin 1000mg twice daily\n\nNew medications started this admission:\n"
            "- Apixaban 5mg twice daily for new atrial fibrillation\n\nDiscontinued:\n"
            "- Aspirin 81mg daily (discontinued due to apixaban initiation)\n\nFollow up with cardiology in 2 weeks."
        ),
        "medications": [
            {"name": "Atorvastatin", "dosage": "40mg", "frequency": "nightly", "status": "continued"},
            {"name": "Lisinopril", "dosage": "20mg", "frequency": "daily", "status": "continued"},
            {"name": "Metformin", "dosage": "1000mg", "frequency": "twice daily", "status": "continued"},
            {"name": "Apixaban", "dosage": "5mg", "frequency": "twice daily", "status": "started"},
            {"name": "Aspirin", "dosage": "81mg", "frequency": "daily", "status": "discontinued"},
        ],
        "observations": [],
    },
]
