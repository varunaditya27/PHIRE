"""
Unit tests for ml/graph/observations.py's extraction logic (pure, no
Neo4j dependency). See test_graph_integration.py for the live write path.
"""

from ml.graph.observations import _find_document_date, _split_value, extract_observations

TABLE_HTML = (
    "<table>\n"
    "<tr><th>Test</th><th>Result</th><th>Reference Range</th><th>Flag</th></tr>\n"
    "<tr><td>Sodium</td><td>138 mEq/L</td><td>136-145</td><td>Normal</td></tr>\n"
    "<tr><td>Potassium</td><td>5.4 mEq/L</td><td>3.5-5.0</td><td>High</td></tr>\n"
    "</table>"
)


def test_split_value_separates_number_and_unit():
    assert _split_value("138 mEq/L") == (138.0, "mEq/L")
    assert _split_value("9.1 mg/dL") == (9.1, "mg/dL")


def test_split_value_handles_bare_number():
    assert _split_value("97") == (97.0, None)


def test_split_value_returns_none_for_unparseable_value():
    assert _split_value("N/A") == (None, None)


def test_find_document_date_extracts_iso_date():
    text = "Riverside Medical Group\nDate of Service: 2026-03-01\n\nSodium: 138 mEq/L"
    assert _find_document_date(text) == "2026-03-01"


def test_find_document_date_falls_back_to_today_when_absent():
    from datetime import date
    assert _find_document_date("no date anywhere in this text") == date.today().isoformat()


def test_extract_observations_from_test_result_table():
    text = f"Riverside Medical Group\nDate of Service: 2026-03-01\n\n{TABLE_HTML}"
    observations = extract_observations(text, document_id="doc123")

    assert len(observations) == 2
    sodium = next(o for o in observations if o["test_name"] == "Sodium")
    assert sodium == {
        "id": "doc123:sodium", "test_name": "Sodium", "raw_value": "138 mEq/L",
        "value": 138.0, "unit": "mEq/L", "reference_range": "136-145", "flag": "Normal",
        "date": "2026-03-01",
    }


def test_extract_observations_skips_non_test_result_tables():
    # An immunization-record-shaped table (Vaccine/Date/Lot#/Site) has no
    # Test/Result columns and should be silently skipped, not mis-parsed.
    other_table = (
        "<table><tr><th>Vaccine</th><th>Date</th></tr>"
        "<tr><td>Influenza</td><td>2025-10-12</td></tr></table>"
    )
    assert extract_observations(other_table, document_id="doc123") == []


def test_extract_observations_returns_empty_list_for_no_tables():
    assert extract_observations("just plain prose, no tables", document_id="doc123") == []
