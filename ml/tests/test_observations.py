"""
Unit tests for ml/graph/observations.py's build logic (pure, no Neo4j
dependency). See test_graph_integration.py for the live write path.
"""

from ml.graph.observations import _split_value, build_prose_observations, build_table_observations, find_document_date

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
    assert find_document_date(text) == "2026-03-01"


def test_find_document_date_falls_back_to_today_when_absent():
    from datetime import date
    assert find_document_date("no date anywhere in this text") == date.today().isoformat()


def test_build_table_observations_from_test_result_table():
    text = f"Riverside Medical Group\nDate of Service: 2026-03-01\n\n{TABLE_HTML}"
    observations = build_table_observations(text, document_id="doc123")

    assert len(observations) == 2
    sodium = next(o for o in observations if o["code"] == "Sodium")
    assert sodium == {
        "id": "doc123:sodium", "code": "Sodium", "raw_value": "138 mEq/L",
        "value": 138.0, "unit": "mEq/L", "reference_range": "136-145", "interpretation": "Normal",
        "effective": "2026-03-01",
    }


def test_build_table_observations_skips_non_test_result_tables():
    # An immunization-record-shaped table (Vaccine/Date/Lot#/Site) has no
    # Test/Result columns and should be silently skipped, not mis-parsed.
    other_table = (
        "<table><tr><th>Vaccine</th><th>Date</th></tr>"
        "<tr><td>Influenza</td><td>2025-10-12</td></tr></table>"
    )
    assert build_table_observations(other_table, document_id="doc123") == []


def test_build_table_observations_returns_empty_list_for_no_tables():
    assert build_table_observations("just plain prose, no tables", document_id="doc123") == []


def test_build_prose_observations_from_extracted_facts():
    raw = [{"name": "Cardiothoracic ratio", "value": "0.48"}]
    text = "Radiology Report\nDate: 2026-02-20\n\nCardiothoracic ratio measured at 0.48."

    observations = build_prose_observations(raw, text, document_id="doc456")

    assert observations == [{
        "id": "doc456:cardiothoracic_ratio", "code": "Cardiothoracic ratio", "raw_value": "0.48",
        "value": 0.48, "unit": None, "reference_range": None, "interpretation": None,
        "effective": "2026-02-20",
    }]


def test_build_prose_observations_skips_entries_missing_name_or_value():
    raw = [{"name": "", "value": "0.48"}, {"name": "Something"}]
    assert build_prose_observations(raw, "no date here", document_id="doc456") == []


def test_build_table_observations_canonicalizes_metric_names():
    # The exact bug found live: a table using "LDL" as its column value
    # and another document's table using "LDL Cholesterol" produced two
    # separate Observation nodes for the same lab test.
    table = "<table><tr><th>Test</th><th>Result</th></tr><tr><td>LDL</td><td>162 mg/dL</td></tr></table>"
    observations = build_table_observations(table, document_id="doc1", effective_date="2026-03-10")
    assert observations[0]["code"] == "LDL Cholesterol"


def test_build_prose_observations_canonicalizes_metric_names():
    raw = [{"name": "LDL cholesterol", "value": "191 mg/dL"}]
    observations = build_prose_observations(raw, "text", document_id="doc2", effective_date="2026-03-01")
    assert observations[0]["code"] == "LDL Cholesterol"
