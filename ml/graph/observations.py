"""
Builds and writes typed Observation records to Neo4j — primarily from
Lift VLM structured visual extraction (build_lift_observations) and
legacy/table extraction helpers, normalized to the same shape before writing.

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

from html.parser import HTMLParser
import re

from ml.graph.client import GraphClient
from ml.graph.document_dates import find_document_date
from ml.graph.metric_resolver import resolve_metric

_TABLE_RE = re.compile(r"<table>.*?</table>", re.DOTALL)


class _TableRowParser(HTMLParser):
    """Collects <tr> rows (each a list of cell strings) from one table block."""

    def __init__(self) -> None:
        super().__init__()
        self.row_cells: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "tr":
            self._current_row = []
        elif tag in ("td", "th"):
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._current_cell is not None and self._current_row is not None:
            self._current_row.append("".join(self._current_cell).strip())
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None:
            self.row_cells.append(self._current_row)
            self._current_row = None

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)


def find_table_blocks(text: str) -> list[str]:
    """Return every <table>...</table> substring in text, in document order."""
    return _TABLE_RE.findall(text)


def parse_table_rows(table_html: str) -> list[dict[str, str]]:
    """Parse one HTML table into a list of header-label -> cell-value dicts."""
    parser = _TableRowParser()
    parser.feed(table_html)
    if not parser.row_cells:
        return []
    headers, *data_rows = parser.row_cells
    return [dict(zip(headers, row)) for row in data_rows]


DEFAULT_PATIENT_ID = "self"

# Leading "-" is optional but real: some panels (e.g. base excess on a
# blood gas panel) report legitimately negative values -- found via
# review, "-3.2 mEq/L" silently failed to parse as numeric under a
# digit/dot-only pattern, dropping that observation out of every
# value-based feature (trend deltas, latest-value dedup) even though its
# raw_value was still stored.
_VALUE_RE = re.compile(r"^(-?[\d.]+)\s*(.*)$")

# A compound reading ("148/92 mmHg" -- systolic/diastolic blood pressure)
# isn't representable by this schema's single value+unit pair. Without
# this guard, _VALUE_RE still matched the leading number and silently
# truncated to (148.0, "/92 mmHg") -- a wrong, half-discarded value with
# a corrupted unit string, not a graceful "unparseable." Found via review:
# metric_resolver.py already aliases "Blood Pressure"/"bp" as an
# anticipated real metric, so prose extraction on a real progress note
# ("...148/92 mmHg") reaches this. Excluded explicitly (returns
# unparseable, like "N/A") rather than guessing which number to keep --
# representing blood pressure properly needs a two-value schema decision,
# which is a scope call for GRAPH_SCHEMA_ROADMAP.md, not something to
# silently half-implement here.
_COMPOUND_VALUE_RE = re.compile(r"^-?\d+(\.\d+)?\s*/\s*-?\d+(\.\d+)?")


def _split_value(raw_value: str) -> tuple[float | None, str | None]:
    """Split "138 mEq/L" into (138.0, "mEq/L") for numeric querying; (None, None) if unparseable.

    (None, None) for a compound "systolic/diastolic" reading too, not a
    truncated single number -- see _COMPOUND_VALUE_RE.
    """
    stripped = raw_value.strip()
    if _COMPOUND_VALUE_RE.match(stripped):
        return None, None
    match = _VALUE_RE.match(stripped)
    if not match:
        return None, None
    try:
        return float(match.group(1)), (match.group(2).strip() or None)
    except ValueError:
        return None, None


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
    """Attach a stable id + effective date to raw observation dicts from free-text extraction."""
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


def build_lift_observations(
    observations: list[dict],
    document_id: str,
    effective_date: str | None = None,
    *args,
    **kwargs,
) -> list[dict]:
    """Attach stable id and normalized fields to Lift-extracted observations.

    Preserves unit, reference_range, and interpretation produced by Lift.
    Supports both (observations, document_id, effective_date) and
    (observations, document_text, document_id, effective_date) signatures.
    """
    if args:
        document_id, effective_date = effective_date, args[0]

    result = []
    for obs in observations:
        code = obs.get("name")
        val_str = str(obs.get("value", "")).strip()
        if not code or not val_str:
            continue
        code = resolve_metric(code)
        value, parsed_unit = _split_value(val_str)
        unit = obs.get("unit")
        if unit is not None:
            unit = str(unit).strip() or None
        else:
            unit = parsed_unit

        raw_value = val_str
        if unit and unit not in val_str:
            raw_value = f"{val_str} {unit}"

        result.append({
            "id": _stable_id(document_id, code),
            "code": code,
            "raw_value": raw_value,
            "value": value,
            "unit": unit,
            "reference_range": obs.get("reference_range") or None,
            "interpretation": obs.get("interpretation") or None,
            "effective": effective_date,
        })
        if code == "Blood Pressure":
            result.extend(_blood_pressure_components(val_str, unit, document_id, effective_date))
    return result


def _blood_pressure_components(val_str: str, unit: str | None, document_id: str, effective_date: str | None) -> list[dict]:
    """Numeric systolic/diastolic observations for a "148/92" reading.

    The compound observation stays as-is (readable, and what NLI verifies a
    "148/92" claim against) but has no numeric value, so it can't be charted
    or trended. These two derived observations carry the numbers, which lets
    the timeline plot BP and get_trend_facts report systolic/diastolic change.
    """
    match = _COMPOUND_VALUE_RE.match(val_str)
    if not match:
        return []
    unit = unit or "mmHg"
    systolic, diastolic = (float(n) for n in re.split(r"\s*/\s*", match.group(0)))
    return [
        {
            "id": _stable_id(document_id, name),
            "code": name,
            "raw_value": f"{number:g} {unit}",
            "value": number,
            "unit": unit,
            "reference_range": None,
            "interpretation": None,
            "effective": effective_date,
        }
        for name, number in (("Blood Pressure (Systolic)", systolic), ("Blood Pressure (Diastolic)", diastolic))
    ]


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
