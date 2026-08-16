"""
Unit tests for ml/rag/ingest/chunking.py's chunk_ocr_text: the three
content shapes patient documents mix (HTML tables, label:value lines,
prose paragraphs) each need different chunking, verified independently
and combined.
"""

from ml.rag.ingest.chunking import chunk_ocr_text

TABLE_HTML = (
    "<table>\n"
    "<tr><th>Test</th><th>Result</th></tr>\n"
    "<tr><td>Sodium</td><td>138 mEq/L</td></tr>\n"
    "<tr><td>Potassium</td><td>5.4 mEq/L</td></tr>\n"
    "</table>"
)


def test_chunk_ocr_text_gives_one_chunk_per_table_row():
    chunks = chunk_ocr_text(TABLE_HTML)
    assert chunks == ["Test: Sodium, Result: 138 mEq/L", "Test: Potassium, Result: 5.4 mEq/L"]


def test_chunk_ocr_text_splits_label_value_lines_individually():
    text = "LDL Cholesterol: 162 mg/dL (High)\nHDL Cholesterol: 38 mg/dL (Low)"
    assert chunk_ocr_text(text) == [
        "LDL Cholesterol: 162 mg/dL (High)",
        "HDL Cholesterol: 38 mg/dL (Low)",
    ]


def test_chunk_ocr_text_keeps_prose_paragraph_whole():
    paragraph = "Patient presents with hypertension. Blood pressure remains elevated despite treatment."
    assert chunk_ocr_text(paragraph) == [paragraph]


def test_chunk_ocr_text_distinguishes_prose_paragraphs_by_blank_line():
    text = (
        "First paragraph is one long continuous line of prose text with no breaks in it at all.\n"
        "\n"
        "Second paragraph is also one long continuous line of prose with no internal breaks either."
    )
    chunks = chunk_ocr_text(text)
    assert len(chunks) == 2
    assert chunks[0].startswith("First paragraph")
    assert chunks[1].startswith("Second paragraph")


def test_chunk_ocr_text_handles_mixed_document():
    text = (
        "Riverside Medical Group - Comprehensive Metabolic Panel\n"
        "Patient: R. Thompson    Date of Service: 2026-03-01\n"
        "\n"
        f"{TABLE_HTML}\n"
        "\n"
        "Impression: results reviewed with patient during today's visit and follow-up scheduled."
    )
    chunks = chunk_ocr_text(text)

    assert "Riverside Medical Group - Comprehensive Metabolic Panel" in chunks
    assert "Patient: R. Thompson    Date of Service: 2026-03-01" in chunks
    assert "Test: Sodium, Result: 138 mEq/L" in chunks
    assert "Test: Potassium, Result: 5.4 mEq/L" in chunks
    assert any(c.startswith("Impression:") for c in chunks)
    # No raw HTML tags leaked into any chunk.
    assert not any("<" in c for c in chunks)


def test_chunk_ocr_text_splits_oversized_prose_paragraph():
    long_paragraph = "This is a long sentence that keeps going. " * 30
    chunks = chunk_ocr_text(long_paragraph, max_chars=200)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
