"""
Builds and writes typed Observation records to Neo4j — from both
table_parsing.py's deterministic table extraction and
prose_extraction.py's LLM-based free-text extraction, normalized to the
same shape before writing.

Schema (FHIR-inspired field names — code/value/effective/interpretation
mirror FHIR's Observation resource; see docs/GRAPH_SCHEMA_ROADMAP.md for
why full FHIR modeling isn't adopted, just the field vocabulary):

    (:Patient {id})-[:HAS_OBSERVATION]->(:Observation)-[:FROM_DOCUMENT]->(:Document)

Patient is a single well-known node ("self") — PHIRE runs one instance
per person (see CLAUDE.md's local-only, single-user framing), so there's
no multi-patient schema to design around yet. Observation ids are stable
(document_id + code), so re-ingesting a document updates its Observations
via MERGE rather than duplicating them.
"""

import re
from datetime import date

from ml.graph.client import GraphClient
from ml.graph.metric_resolver import resolve_metric
from ml.rag.ingest.table_parsing import find_table_blocks, parse_table_rows

DEFAULT_PATIENT_ID = "self"

_VALUE_RE = re.compile(r"^([\d.]+)\s*(.*)$")
_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def _split_value(raw_value: str) -> tuple[float | None, str | None]:
    """Split "138 mEq/L" into (138.0, "mEq/L") for numeric querying; (None, None) if unparseable."""
    match = _VALUE_RE.match(raw_value.strip())
    if not match:
        return None, None
    try:
        return float(match.group(1)), (match.group(2).strip() or None)
    except ValueError:
        return None, None


def find_document_date(text: str) -> str:
    """Best-effort clinical date from the document's own text (e.g. "Date of Service: 2026-03-01").

    Falls back to today's date if none is found — an observation without
    any date is worse than one dated at ingestion time, since the whole
    point of this graph is time-series queries. Shared by
    medications.py/conditions.py too, not just table-derived Observations.
    """
    match = _DATE_RE.search(text)
    return match.group(1) if match else date.today().isoformat()


def _stable_id(document_id: str, code: str) -> str:
    return f"{document_id}:{code.lower().replace(' ', '_')}"


def build_table_observations(
    document_text: str, document_id: str, effective_date: str | None = None,
) -> list[dict]:
    """Parse every Test/Result-shaped table in document_text into observation dicts.

    Only tables with "Test" and "Result" columns are recognized (labs,
    vitals — the shapes actually produced in experiments/eval_data so
    far). A differently-shaped table (e.g. the immunization record's
    Vaccine/Date/Lot#/Site) doesn't match and is silently skipped, not
    mis-typed as a lab result — a real scope limit, not a bug, until a
    second table shape is added deliberately.

    Pass effective_date to skip re-scanning document_text for a date —
    callers that already extracted it once (e.g. ingest_patient_document's
    main(), which calls this alongside build_prose_observations/
    build_medications/build_conditions on the identical text) shouldn't
    each redo the same regex scan.
    """
    effective = effective_date if effective_date is not None else find_document_date(document_text)
    observations = []
    for table_html in find_table_blocks(document_text):
        for row in parse_table_rows(table_html):
            code, raw_value = row.get("Test"), row.get("Result")
            if not code or not raw_value:
                continue
            code = resolve_metric(code)
            value, unit = _split_value(raw_value)
            observations.append({
                "id": _stable_id(document_id, code),
                "code": code,
                "raw_value": raw_value,
                "value": value,
                "unit": unit,
                "reference_range": row.get("Reference Range"),
                "interpretation": row.get("Flag"),
                "effective": effective,
            })
    return observations


def build_prose_observations(
    observations: list[dict], document_text: str, document_id: str, effective_date: str | None = None,
) -> list[dict]:
    """Attach a stable id + effective date to raw observation dicts from prose_extraction.extract_facts."""
    effective = effective_date if effective_date is not None else find_document_date(document_text)
    result = []
    for obs in observations:
        code, raw_value = obs.get("name"), obs.get("value")
        if not code or not raw_value:
            continue
        code = resolve_metric(code)
        value, unit = _split_value(raw_value)
        result.append({
            "id": _stable_id(document_id, code),
            "code": code,
            "raw_value": raw_value,
            "value": value,
            "unit": unit,
            "reference_range": None,
            "interpretation": None,
            "effective": effective,
        })
    return result


def write_observations(
    client: GraphClient, document_id: str, filename: str, observations: list[dict],
    patient_id: str = DEFAULT_PATIENT_ID,
) -> None:
    """Write parsed observations to Neo4j, linked to a Patient and a Document node."""
    if not observations:
        return
    client.run(
        """
        MERGE (p:Patient {id: $patient_id})
        MERGE (d:Document {id: $document_id})
        SET d.filename = $filename
        WITH p, d
        UNWIND $observations AS obs
        MERGE (o:Observation {id: obs.id})
        SET o.code = obs.code, o.raw_value = obs.raw_value, o.value = obs.value,
            o.unit = obs.unit, o.reference_range = obs.reference_range,
            o.interpretation = obs.interpretation, o.effective = obs.effective
        MERGE (p)-[:HAS_OBSERVATION]->(o)
        MERGE (o)-[:FROM_DOCUMENT]->(d)
        """,
        patient_id=patient_id, document_id=document_id, filename=filename, observations=observations,
    )
