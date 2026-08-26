"""
Read-side counterpart to observations.py/medications.py/conditions.py's
build_*/write_* functions: turns the patient's current graph state into
plain-text sentences a chat LLM can read.

This is the missing link ml/chains/qa_chain.py needs — QAChain.answer()
already accepts an observations: list[str] parameter and folds it into the
prompt (ml/llm/prompt_builder.py), but nothing in ml/ ever populated it
from Neo4j. This does.
"""

from ml.graph.client import GraphClient
from ml.graph.observations import DEFAULT_PATIENT_ID


def _fetch_observations(client: GraphClient, patient_id: str) -> list[dict]:
    """Every stored Observation, oldest effective date first."""
    return client.run(
        "MATCH (:Patient {id: $patient_id})-[:HAS_OBSERVATION]->(o:Observation) "
        "RETURN o.code AS code, o.raw_value AS raw_value, o.reference_range AS reference_range, "
        "o.interpretation AS interpretation, o.effective AS effective, o.value AS value, o.unit AS unit "
        "ORDER BY o.effective",
        patient_id=patient_id,
    )


def _format_observation(row: dict) -> str:
    detail = f" (reference range {row['reference_range']})" if row["reference_range"] else ""
    flag = f" -- {row['interpretation']}" if row["interpretation"] else ""
    return f"{row['code']}: {row['raw_value']}{detail}{flag} on {row['effective']}."


def _fetch_medication_facts(client: GraphClient, patient_id: str) -> list[str]:
    facts = []
    for row in client.run(
        "MATCH (:Patient {id: $patient_id})-[:HAS_MEDICATION]->(m:Medication) "
        "RETURN m.code AS code, m.dosage AS dosage, m.frequency AS frequency, m.status AS status",
        patient_id=patient_id,
    ):
        dose = f" {row['dosage']}" if row["dosage"] else ""
        freq = f" {row['frequency']}" if row["frequency"] else ""
        facts.append(f"Medication: {row['code']}{dose}{freq} ({row['status']}).")
    return facts


def _fetch_condition_facts(client: GraphClient, patient_id: str) -> list[str]:
    return [
        f"Condition: {row['code']} ({row['status']})."
        for row in client.run(
            "MATCH (:Patient {id: $patient_id})-[:HAS_CONDITION]->(c:Condition) "
            "RETURN c.code AS code, c.status AS status",
            patient_id=patient_id,
        )
    ]


def get_patient_facts(client: GraphClient, patient_id: str = DEFAULT_PATIENT_ID) -> list[str]:
    """Return every stored Observation/Medication/Condition as one sentence each.

    No filtering or ranking yet -- every stored fact goes in, oldest
    observation first. Fine at PHIRE's current single-patient, few-document
    scale; revisit (real query routing, not just this dedup) once a
    patient has enough history that this stops fitting the LLM's context
    window -- see build_chat_prompt's MAX_CONTEXT_CHARS truncation, which
    is the current backstop if it ever gets too big.

    Full history, on purpose: this feeds the *generation* prompt, where
    trend context ("2024: 121, 2025: 137, 2026: 149") is useful. For
    claim *verification*, see get_current_patient_facts instead -- an
    NLI check needs one current value, not the whole history (see its
    docstring for why).
    """
    return (
        [_format_observation(row) for row in _fetch_observations(client, patient_id)]
        + _fetch_medication_facts(client, patient_id)
        + _fetch_condition_facts(client, patient_id)
    )


def get_current_patient_facts(client: GraphClient, patient_id: str = DEFAULT_PATIENT_ID) -> list[str]:
    """Return the patient's *current* state: latest value per metric, plus all medications/conditions.

    Used for claim verification, not the generation prompt. Checking a
    claim like "your LDL is 162" against the *entire* observation history
    (including an older, different LDL reading) makes NLI flag the older
    reading as contradicting the newer one — verified live: this is
    exactly what happened before this function existed. Medications and
    conditions don't have this problem the same way (MERGE already keys
    them by stable identity, not by date), so they're included in full.
    """
    latest_by_code: dict[str, dict] = {}
    for row in _fetch_observations(client, patient_id):
        # _fetch_observations is ORDER BY o.effective ascending, so each
        # later row for the same code simply overwrites the earlier one.
        latest_by_code[row["code"]] = row

    return (
        [_format_observation(row) for row in latest_by_code.values()]
        + _fetch_medication_facts(client, patient_id)
        + _fetch_condition_facts(client, patient_id)
    )


def get_trend_facts(client: GraphClient, patient_id: str = DEFAULT_PATIENT_ID) -> list[str]:
    """One sentence per metric with 2+ numeric readings: change from the previous reading to the latest.

    Deliberately just latest-vs-previous, not a full multi-point trend
    line -- matches docs/AGGRESSIVE_ROADMAP.md's own scope ("simple:
    compare recent vs. 1-year-ago"), and a longer trend is better shown
    as raw history (get_patient_facts) than compressed into one sentence.

    Computed here in Python, not left for the LLM to work out from raw
    numbers in its context -- arithmetic on stored values is exact and
    deterministic, and an LLM restating "increased by 18" itself is
    exactly the kind of claim ml/claims/verifier.py's NLI check can't
    verify (a single entailment score can't confirm arithmetic). This
    sentence becomes a checkable fact instead -- see qa_chain.py's
    DERIVED relabeling, which trusts a claim that matches one of these
    sentences without asking NLI to do the subtraction itself.
    """
    by_code: dict[str, list[dict]] = {}
    for row in _fetch_observations(client, patient_id):
        if row["value"] is not None:
            by_code.setdefault(row["code"], []).append(row)

    facts = []
    for code, readings in by_code.items():
        if len(readings) < 2:
            continue
        previous, latest = readings[-2], readings[-1]
        delta = latest["value"] - previous["value"]
        direction = "an increase" if delta > 0 else "a decrease" if delta < 0 else "no change"
        unit = latest["unit"] or ""
        facts.append(
            f"{code} changed from {previous['raw_value']} on {previous['effective']} "
            f"to {latest['raw_value']} on {latest['effective']} ({direction} of {abs(delta):.1f} {unit}).".replace("  ", " ")
        )
    return facts
