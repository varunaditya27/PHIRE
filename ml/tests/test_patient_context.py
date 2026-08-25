"""
Unit tests for ml/graph/patient_context.py's read-side logic (formatting,
latest-value-per-metric collapsing, trend-delta computation) against a
fake in-memory GraphClient stand-in that returns canned rows instead of
talking to Neo4j -- so this coverage doesn't depend on a live database
(see test_graph_integration.py for the live round-trip, which is this
module's only other coverage).
"""

from ml.graph.patient_context import get_current_patient_facts, get_patient_facts, get_trend_facts


class _FakeGraphClient:
    """Returns canned rows keyed by a fragment of the query text, mirroring the real Cypher shapes."""

    def __init__(self, observations=None, medications=None, conditions=None) -> None:
        self._observations = observations or []
        self._medications = medications or []
        self._conditions = conditions or []

    def run(self, query: str, **params) -> list[dict]:
        if "HAS_OBSERVATION" in query:
            return self._observations
        if "HAS_MEDICATION" in query:
            return self._medications
        if "HAS_CONDITION" in query:
            return self._conditions
        raise AssertionError(f"unexpected query in test fake: {query}")


def _obs(code, raw_value, effective, value=None, unit=None, reference_range=None, interpretation=None):
    return {
        "code": code, "raw_value": raw_value, "reference_range": reference_range,
        "interpretation": interpretation, "effective": effective, "value": value, "unit": unit,
    }


def test_get_patient_facts_formats_observations_medications_and_conditions():
    client = _FakeGraphClient(
        observations=[_obs("Potassium", "5.4 mEq/L", "2026-03-01", value=5.4, unit="mEq/L",
                            reference_range="3.5-5.0", interpretation="High")],
        medications=[{"code": "lisinopril", "dosage": "20mg", "frequency": "daily", "status": "started"}],
        conditions=[{"code": "hypertension", "status": "active"}],
    )

    facts = get_patient_facts(client, patient_id="self")

    assert facts == [
        "Potassium: 5.4 mEq/L (reference range 3.5-5.0) -- High on 2026-03-01.",
        "Medication: lisinopril 20mg daily (started).",
        "Condition: hypertension (active).",
    ]


def test_get_patient_facts_formats_observation_without_range_or_flag():
    client = _FakeGraphClient(observations=[_obs("Sodium", "138 mEq/L", "2026-03-01", value=138.0, unit="mEq/L")])

    facts = get_patient_facts(client, patient_id="self")

    assert facts == ["Sodium: 138 mEq/L on 2026-03-01."]


def test_get_patient_facts_empty_when_nothing_stored():
    assert get_patient_facts(_FakeGraphClient(), patient_id="self") == []


def test_get_current_patient_facts_keeps_only_the_latest_reading_per_metric():
    # _fetch_observations returns oldest-effective-first (the real Cypher
    # query is ORDER BY o.effective ascending) -- the fake mirrors that
    # ordering contract so the "later row overwrites earlier" logic under
    # test is exercised the same way it would be against real Neo4j.
    client = _FakeGraphClient(observations=[
        _obs("LDL Cholesterol", "191 mg/dL", "2026-03-01", value=191.0, unit="mg/dL"),
        _obs("LDL Cholesterol", "162 mg/dL", "2026-03-10", value=162.0, unit="mg/dL"),
    ])

    current = get_current_patient_facts(client, patient_id="self")

    assert current == ["LDL Cholesterol: 162 mg/dL on 2026-03-10."]


def test_get_current_patient_facts_includes_all_medications_and_conditions():
    client = _FakeGraphClient(
        medications=[{"code": "lisinopril", "dosage": "20mg", "frequency": "daily", "status": "started"}],
        conditions=[{"code": "hypertension", "status": "active"}],
    )

    current = get_current_patient_facts(client, patient_id="self")

    assert current == ["Medication: lisinopril 20mg daily (started).", "Condition: hypertension (active)."]


def test_get_trend_facts_computes_decrease_between_latest_two_readings():
    client = _FakeGraphClient(observations=[
        _obs("LDL Cholesterol", "191 mg/dL", "2025-03-01", value=191.0, unit="mg/dL"),
        _obs("LDL Cholesterol", "162 mg/dL", "2026-03-10", value=162.0, unit="mg/dL"),
    ])

    trends = get_trend_facts(client, patient_id="self")

    assert trends == [
        "LDL Cholesterol changed from 191 mg/dL on 2025-03-01 to 162 mg/dL on 2026-03-10 "
        "(a decrease of 29.0 mg/dL)."
    ]


def test_get_trend_facts_computes_increase_between_latest_two_readings():
    client = _FakeGraphClient(observations=[
        _obs("Weight", "70 kg", "2025-03-01", value=70.0, unit="kg"),
        _obs("Weight", "74 kg", "2026-03-10", value=74.0, unit="kg"),
    ])

    trends = get_trend_facts(client, patient_id="self")

    assert "an increase of 4.0 kg" in trends[0]


def test_get_trend_facts_uses_the_latest_two_readings_not_the_first_two():
    client = _FakeGraphClient(observations=[
        _obs("Weight", "70 kg", "2024-01-01", value=70.0, unit="kg"),
        _obs("Weight", "72 kg", "2025-01-01", value=72.0, unit="kg"),
        _obs("Weight", "74 kg", "2026-01-01", value=74.0, unit="kg"),
    ])

    trends = get_trend_facts(client, patient_id="self")

    assert len(trends) == 1
    assert "from 72 kg on 2025-01-01 to 74 kg on 2026-01-01" in trends[0]


def test_get_trend_facts_empty_when_metric_has_only_one_reading():
    client = _FakeGraphClient(observations=[_obs("Sodium", "138 mEq/L", "2026-03-01", value=138.0, unit="mEq/L")])

    assert get_trend_facts(client, patient_id="self") == []


def test_get_trend_facts_skips_unparseable_observations():
    # An observation whose raw_value didn't parse to a number (_split_value
    # returned None) has value=None -- must not be treated as a numeric
    # reading or crash the delta arithmetic.
    client = _FakeGraphClient(observations=[
        _obs("Culture Result", "N/A", "2026-01-01", value=None, unit=None),
        _obs("Culture Result", "N/A", "2026-02-01", value=None, unit=None),
    ])

    assert get_trend_facts(client, patient_id="self") == []
