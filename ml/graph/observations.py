"""
Extracts typed Observation records from parsed table rows and writes them
to Neo4j — the deterministic half of PHIRE's Longitudinal Health Graph
(see ml/graph/__init__.py).

Schema (minimal, deliberately not built out further until a concrete
graph query need calls for more):

    (:Patient {id})-[:HAS_OBSERVATION]->(:Observation)-[:FROM_DOCUMENT]->(:Document)

Patient is a single well-known node ("self") — PHIRE runs one instance
per person (see CLAUDE.md's local-only, single-user framing), so there's
no multi-patient schema to design around yet. Observation ids are stable
(document_id + test name), so re-ingesting a document updates its
Observations via MERGE rather than duplicating them.
"""

import re
from datetime import date

from ml.graph.client import GraphClient
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


def _find_document_date(text: str) -> str:
    """Best-effort clinical date from the document's own text (e.g. "Date of Service: 2026-03-01").

    Falls back to today's date if none is found — an observation without
    any date is worse than one dated at ingestion time, since the whole
    point of this graph is time-series queries.
    """
    match = _DATE_RE.search(text)
    return match.group(1) if match else date.today().isoformat()


def extract_observations(document_text: str, document_id: str) -> list[dict]:
    """Parse every Test/Result-shaped table in document_text into observation dicts.

    Only tables with "Test" and "Result" columns are recognized (labs,
    vitals — the shapes actually produced in experiments/eval_data so
    far). A differently-shaped table (e.g. the immunization record's
    Vaccine/Date/Lot#/Site) doesn't match and is silently skipped, not
    mis-typed as a lab result — a real scope limit, not a bug, until a
    second table shape is added deliberately.
    """
    observation_date = _find_document_date(document_text)
    observations = []
    for table_html in find_table_blocks(document_text):
        for row in parse_table_rows(table_html):
            test_name, raw_value = row.get("Test"), row.get("Result")
            if not test_name or not raw_value:
                continue
            value, unit = _split_value(raw_value)
            observations.append({
                "id": f"{document_id}:{test_name.lower().replace(' ', '_')}",
                "test_name": test_name,
                "raw_value": raw_value,
                "value": value,
                "unit": unit,
                "reference_range": row.get("Reference Range"),
                "flag": row.get("Flag"),
                "date": observation_date,
            })
    return observations


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
        SET o.test_name = obs.test_name, o.raw_value = obs.raw_value, o.value = obs.value,
            o.unit = obs.unit, o.reference_range = obs.reference_range, o.flag = obs.flag, o.date = obs.date
        MERGE (p)-[:HAS_OBSERVATION]->(o)
        MERGE (o)-[:FROM_DOCUMENT]->(d)
        """,
        patient_id=patient_id, document_id=document_id, filename=filename, observations=observations,
    )
