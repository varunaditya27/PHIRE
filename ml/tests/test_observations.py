"""
Unit tests for ml/graph/observations.py's build logic (pure, no Neo4j
dependency). See test_graph_integration.py for the live write path.
"""

from ml.graph.observations import (
    _split_value,
    build_lift_observations,
    build_prose_observations,
    build_table_observations,
)

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


def test_split_value_handles_negative_numbers():
    # A legitimately negative lab value (e.g. base excess on a blood gas
    # panel) must still parse as numeric, not silently drop out of every
    # value-based feature (trend deltas, latest-value dedup).
    assert _split_value("-3.2 mEq/L") == (-3.2, "mEq/L")
    assert _split_value("-5") == (-5.0, None)


def test_split_value_returns_none_for_a_compound_blood_pressure_reading():
    # Regression: this used to silently truncate to (148.0, "/92 mmHg")
    # -- a wrong, half-discarded value with a corrupted unit, since
    # _VALUE_RE matched the leading systolic number and swallowed the
    # rest as "unit." A compound reading isn't representable by this
    # schema's single value+unit pair, so it must come back unparseable,
    # like "N/A" -- not a plausible-looking wrong number.
    assert _split_value("148/92 mmHg") == (None, None)
    assert _split_value("120/80") == (None, None)


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


def test_build_lift_observations_preserves_units_range_and_interpretation():
    raw = [{
        "name": "LDL",
        "value": "162",
        "unit": "mg/dL",
        "reference_range": "0-100",
        "interpretation": "High",
    }]
    observations = build_lift_observations(raw, document_id="doc1", effective_date="2026-03-10")
    assert len(observations) == 1
    assert observations[0] == {
        "id": "doc1:ldl_cholesterol",
        "code": "LDL Cholesterol",
        "raw_value": "162 mg/dL",
        "value": 162.0,
        "unit": "mg/dL",
        "reference_range": "0-100",
        "interpretation": "High",
        "effective": "2026-03-10",
    }


def test_lift_blood_pressure_adds_numeric_systolic_and_diastolic_observations():
    result = build_lift_observations(
        [{"name": "Blood Pressure", "value": "148/92", "unit": "mmHg", "interpretation": "High"}],
        "doc1", "2026-03-12",
    )
    by_code = {o["code"]: o for o in result}

    # compound reading preserved for display / NLI, still non-numeric
    assert by_code["Blood Pressure"]["raw_value"] == "148/92 mmHg"
    assert by_code["Blood Pressure"]["value"] is None
    assert (by_code["Blood Pressure (Systolic)"]["value"], by_code["Blood Pressure (Systolic)"]["unit"]) == (148.0, "mmHg")
    assert by_code["Blood Pressure (Diastolic)"]["value"] == 92.0
    assert by_code["Blood Pressure (Systolic)"]["id"] != by_code["Blood Pressure (Diastolic)"]["id"]


def test_lift_non_bp_compound_value_is_not_split():
    result = build_lift_observations([{"name": "Albumin/Globulin Ratio", "value": "1.2/1"}], "doc1", "2026-03-12")
    assert len(result) == 1
