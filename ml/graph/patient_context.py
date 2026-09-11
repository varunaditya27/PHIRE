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
from ml.graph.reference_ranges import TOPIC_MARKERS, classify, get_reference_range


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


def get_reference_range_facts(client: GraphClient, patient_id: str = DEFAULT_PATIENT_ID) -> list[str]:
    """One sentence per current observation classifying it against a standard reference range.

    Only for markers the source document itself didn't already print a
    reference_range/interpretation for (see ml/graph/reference_ranges.py's
    docstring) -- if the report says "High" itself, that's already a
    direct fact via _format_observation, and this would be redundant.
    Same DERIVED mechanism as get_trend_facts: the low/normal/high
    classification is computed here in Python (exact, deterministic),
    not left for the LLM to work out or for NLI to confirm on its own.
    """
    latest_by_code: dict[str, dict] = {}
    for row in _fetch_observations(client, patient_id):
        latest_by_code[row["code"]] = row

    facts = []
    for row in latest_by_code.values():
        if row["reference_range"] or row["interpretation"] or row["value"] is None:
            continue
        ref = get_reference_range(row["code"])
        if ref is None:
            continue
        label = classify(row["value"], ref)
        facts.append(
            f"{row['code']} of {row['raw_value']} is {label} "
            f"(standard reference range: {ref.citation})."
        )
    return facts


def get_topic_marker_facts(client: GraphClient, topic: str, patient_id: str = DEFAULT_PATIENT_ID) -> tuple[list[str], list[str]]:
    """(facts, missing_markers) for a health topic (see
    ml.graph.reference_ranges.TOPIC_MARKERS/detect_topic).

    Lets a question like "do I have diabetes" or "is my thyroid normal"
    be answered by directly checking exactly the markers that matter for
    that topic, instead of retrieval + an LLM free-associating over
    whatever's in the patient's full panel (which, for a topic the
    uploaded reports don't cover, tends to make the model discuss
    unrelated markers instead of just saying so -- found live). Each
    fact prefers the report's own printed interpretation/reference_range
    over the computed one, same precedence as get_reference_range_facts.
    missing_markers lists topic markers this patient has no reading for
    at all, so the caller can say so plainly rather than silently
    omitting them.
    """
    latest_by_code: dict[str, dict] = {}
    for row in _fetch_observations(client, patient_id):
        latest_by_code[row["code"]] = row

    facts: list[str] = []
    missing: list[str] = []
    for marker in TOPIC_MARKERS.get(topic, []):
        row = latest_by_code.get(marker)
        if row is None or row["value"] is None:
            missing.append(marker)
            continue
        if row["reference_range"] or row["interpretation"]:
            facts.append(_format_observation(row))
            continue
        ref = get_reference_range(marker)
        if ref is not None:
            label = classify(row["value"], ref)
            facts.append(f"{marker} of {row['raw_value']} is {label} (standard reference range: {ref.citation}).")
        else:
            facts.append(f"{marker} was {row['raw_value']} on {row['effective']}.")
    return facts, missing
