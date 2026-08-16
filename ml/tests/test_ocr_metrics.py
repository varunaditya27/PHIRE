"""Unit tests for ml/rag/ingest/experiments/metrics.py's CER/WER/field-accuracy scoring."""

from ml.rag.ingest.experiments.metrics import (
    character_error_rate,
    content_character_error_rate,
    field_accuracy,
    strip_markup,
    word_error_rate,
)


def test_character_error_rate_is_zero_for_exact_match():
    assert character_error_rate("LDL: 162 mg/dL", "LDL: 162 mg/dL") == 0.0


def test_character_error_rate_reflects_edit_distance():
    # "cot" -> "cat" is 1 substitution over a 3-char reference
    assert character_error_rate("cot", "cat") == 1 / 3


def test_character_error_rate_handles_empty_reference():
    assert character_error_rate("", "") == 0.0
    assert character_error_rate("stray text", "") == 1.0


def test_word_error_rate_is_zero_for_exact_match():
    assert word_error_rate("the LDL is high", "the LDL is high") == 0.0


def test_word_error_rate_reflects_word_edit_distance():
    assert word_error_rate("the LDL is low", "the LDL is high") == 1 / 4


def test_field_accuracy_all_fields_present():
    text = "LDL Cholesterol: 178 mg/dL (High)\nHDL Cholesterol: 41 mg/dL (Low)"
    fields = {"LDL Cholesterol": "178 mg/dL", "HDL Cholesterol": "41 mg/dL"}
    assert field_accuracy(text, fields) == 1.0


def test_field_accuracy_partial_when_value_wrong():
    text = "LDL Cholesterol: 187 mg/dL (High)\nHDL Cholesterol: 41 mg/dL (Low)"
    fields = {"LDL Cholesterol": "178 mg/dL", "HDL Cholesterol": "41 mg/dL"}
    # digits transposed (178 -> 187): label present, value not -> miss
    assert field_accuracy(text, fields) == 0.5


def test_field_accuracy_tolerates_whitespace_differences():
    text = "LDL   Cholesterol:    178   mg/dL"
    fields = {"LDL Cholesterol": "178 mg/dL"}
    assert field_accuracy(text, fields) == 1.0


def test_field_accuracy_empty_fields_returns_zero():
    assert field_accuracy("any text", {}) == 0.0


def test_strip_markup_removes_html_table_tags():
    html = "<table><tr><td>Sodium</td><td>138 mEq/L</td></tr></table>"
    assert strip_markup(html) == "Sodium 138 mEq/L"


def test_strip_markup_removes_markdown_table_syntax():
    markdown = "| Test | Result |\n|------|--------|\n| Sodium | 138 mEq/L |"
    assert strip_markup(markdown) == "Test Result Sodium 138 mEq/L"


def test_content_cer_treats_html_and_markdown_tables_as_equivalent():
    html = "<table><tr><td>Sodium</td><td>138 mEq/L</td></tr></table>"
    markdown = "| Sodium | 138 mEq/L |"
    reference = "Sodium 138 mEq/L"
    # Both markup styles should score identically once normalized, even
    # though raw CER against plain-text reference would heavily penalize
    # the HTML version for its extra tag characters.
    assert content_character_error_rate(html, reference) == content_character_error_rate(markdown, reference)
    assert character_error_rate(html, reference) > character_error_rate(markdown, reference)
