from ml.rag.ingest.chunk_synthesizer import synthesize_patient_chunks


def test_synthesize_patient_chunks_creates_structured_sentences():
    payload = {
        "document_date": "2026-03-10",
        "document_type": "Lipid Panel",
        "observations": [
            {
                "name": "LDL Cholesterol",
                "value": "162",
                "unit": "mg/dL",
                "reference_range": "0-100",
                "interpretation": "High",
            },
            {
                "name": "HDL Cholesterol",
                "value": "45",
                "unit": "mg/dL",
                "reference_range": "> 40",
                "interpretation": "Normal",
            },
        ],
        "medications": [
            {
                "name": "Atorvastatin",
                "dosage": "20 mg",
                "frequency": "once daily",
                "status": "started",
            }
        ],
        "conditions": [
            {
                "name": "Hyperlipidemia",
                "status": "active",
            }
        ],
        "narrative_sections": [
            {
                "heading": "Impression",
                "content": "Patient presents with elevated atherogenic lipids.",
            }
        ],
    }

    chunks = synthesize_patient_chunks(
        payload=payload,
        document_id="doc123",
        filename="report.pdf",
        authority=1.0,
    )

    # 2 observations + 1 medication + 1 condition + 1 narrative = 5 chunks
    assert len(chunks) == 5

    # Check observation sentence format
    ldl_chunk = chunks[0]
    assert "LDL Cholesterol was 162 mg/dL" in ldl_chunk.text
    assert "Reference Range: 0-100" in ldl_chunk.text
    assert "Interpretation: High" in ldl_chunk.text
    assert ldl_chunk.metadata["document_id"] == "doc123"
    assert ldl_chunk.metadata["source"] == "patient_document"
    assert ldl_chunk.metadata["authority"] == 1.0

    # Check medication sentence format
    med_chunk = chunks[2]
    assert "Atorvastatin (20 mg, once daily) - Status: started" in med_chunk.text

    # Check condition sentence format
    cond_chunk = chunks[3]
    assert "Condition: Hyperlipidemia (Status: active)" in cond_chunk.text

    # Check narrative sentence format
    narrative_chunk = chunks[4]
    assert "[Impression] Patient presents with elevated atherogenic lipids." in narrative_chunk.text


def test_synthesize_patient_chunks_handles_sparse_entities():
    sparse_payload = {
        "document_date": None,
        "observations": [{"name": "Glucose", "value": "95"}],
        "medications": [],
        "conditions": [],
        "narrative_sections": [],
    }
    chunks = synthesize_patient_chunks(sparse_payload, "doc456", "sparse.png")
    assert len(chunks) == 1
    assert "Glucose was 95" in chunks[0].text
