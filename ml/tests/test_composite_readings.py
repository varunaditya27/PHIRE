"""Unit tests for ml/graph/composite_readings.py and its use by build_lift_observations."""

import pytest

from ml.graph.composite_readings import expand
from ml.graph.observations import build_lift_observations


@pytest.mark.parametrize("value", ["148/92", "148/92 mmHg", "148 / 92", "148/92 mm Hg"])
def test_blood_pressure_splits_into_systolic_and_diastolic(value):
    result = expand("Blood Pressure", value, None)

    assert result.primary is None
    assert result.extras == [
        ("Blood Pressure (Systolic)", 148.0, "mmHg"),
        ("Blood Pressure (Diastolic)", 92.0, "mmHg"),
    ]


@pytest.mark.parametrize("value", ["148/92 (76)", "148/92, HR 76", "148/92 mmHg, pulse 76 bpm", "148/92; 76"])
def test_blood_pressure_with_pulse_also_yields_heart_rate(value):
    assert ("Heart Rate", 76.0, "bpm") in expand("Blood Pressure", value, "mmHg").extras


@pytest.mark.parametrize("value", ["1/2", "120/80/60", "high", "148/92 mmHg and rising"])
def test_malformed_blood_pressure_is_left_alone(value):
    assert expand("Blood Pressure", value, None) is None


def test_snellen_fraction_becomes_decimal_acuity():
    assert expand("Visual Acuity", "20/40", None).primary == (0.5, "decimal")
    assert expand("Visual Acuity", "6/6", None).primary == (1.0, "decimal")
    assert expand("Visual Acuity", "20/0", None) is None


@pytest.mark.parametrize("value,cm", [("5'11\"", 180.3), ("5 ft 11 in", 180.3), ("6'", 182.9), ("5 feet 6 inches", 167.6)])
def test_height_feet_inches_becomes_centimetres(value, cm):
    assert expand("Height", value, None).primary == (cm, "cm")


@pytest.mark.parametrize("value", ["172 cm", "1.72 m", "tall"])
def test_plain_height_is_not_a_composite(value):
    assert expand("Height", value, None) is None


@pytest.mark.parametrize("name", ["Albumin/Globulin Ratio", "HbA1c", "LDL Cholesterol"])
def test_unregistered_metrics_are_never_expanded(name):
    assert expand(name, "1.2/1", None) is None


def test_build_lift_observations_adds_bp_components_and_keeps_compound_text():
    result = build_lift_observations(
        [{"name": "BP", "value": "148/92", "unit": "mmHg", "interpretation": "High"}], "doc1", "2026-03-12",
    )
    by_code = {o["code"]: o for o in result}

    assert by_code["Blood Pressure"]["raw_value"] == "148/92 mmHg"  # alias "BP" resolved; text kept for NLI
    assert by_code["Blood Pressure"]["value"] is None
    assert by_code["Blood Pressure (Systolic)"]["value"] == 148.0
    assert by_code["Blood Pressure (Diastolic)"]["value"] == 92.0
    assert len({o["id"] for o in result}) == 3


def test_build_lift_observations_converts_height_and_acuity_in_place():
    result = build_lift_observations(
        [{"name": "Height", "value": "5'11\""}, {"name": "Vision", "value": "20/40"}], "doc1", "2026-03-12",
    )
    by_code = {o["code"]: o for o in result}

    assert (by_code["Height"]["value"], by_code["Height"]["unit"]) == (180.3, "cm")
    assert by_code["Height"]["raw_value"] == "5'11\""  # what the document said is preserved
    assert (by_code["Visual Acuity"]["value"], by_code["Visual Acuity"]["unit"]) == (0.5, "decimal")
    assert len(result) == 2  # no extras for these


def test_non_composite_slash_value_is_not_split():
    result = build_lift_observations([{"name": "Albumin/Globulin Ratio", "value": "1.2/1"}], "doc1", "2026-03-12")
    assert len(result) == 1


def test_qualified_names_match_their_base_and_keep_the_qualifier_on_derived_observations():
    acuity = expand("Visual acuity (right eye)", "20/40", None)
    bp = expand("Blood Pressure (sitting)", "148/92, pulse 76", None)

    assert acuity.primary == (0.5, "decimal")
    assert [name for name, _, _ in bp.extras] == [
        "Blood Pressure (Systolic, sitting)", "Blood Pressure (Diastolic, sitting)", "Heart Rate (sitting)",
    ]


def test_two_eyes_stay_separate_series_in_built_observations():
    result = build_lift_observations(
        [{"name": "Visual acuity (right eye)", "value": "20/20"}, {"name": "Visual acuity (left eye)", "value": "20/40"}],
        "doc1", "2026-03-12",
    )

    assert [(o["code"], o["value"]) for o in result] == [
        ("Visual acuity (right eye)", 1.0), ("Visual acuity (left eye)", 0.5),
    ]
    assert len({o["id"] for o in result}) == 2
