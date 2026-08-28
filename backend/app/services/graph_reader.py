"""
Read structured patient facts (observations, medications, conditions)
from ml/graph's Neo4j Longitudinal Health Graph.

Backs GET /api/observations and GET /api/timeline. Queries the graph
schema documented in ml/graph/observations.py/medications.py/
conditions.py directly via GraphClient.run() (ml/'s public Cypher-execution
API) rather than ml.graph.patient_context's get_patient_facts() etc --
those return pre-formatted prose sentences for the chat prompt, not the
structured fields (code/value/unit/date) this API's response contract
needs.

Schema (see ml/graph/observations.py for the authoritative version):
    (:Patient {id:"self"})-[:HAS_OBSERVATION]->(:Observation {code, raw_value, value, unit, reference_range, interpretation, effective})
    (:Patient {id:"self"})-[:HAS_MEDICATION]->(:Medication {code, dosage, frequency, status, effective})
    (:Patient {id:"self"})-[:HAS_CONDITION]->(:Condition {code, status, effective})
    (...)-[:FROM_DOCUMENT]->(:Document {id, filename})
"""

from datetime import date, datetime

from app.models.observation import ObservationRead, TimelinePoint, TimelineResponse, TimelineSeries
from app.services.ml_singletons import new_graph_client
from app.utils.constants import ObservationType

_OBSERVATION_QUERY = """
MATCH (:Patient {id: $patient_id})-[:HAS_OBSERVATION]->(o:Observation)
OPTIONAL MATCH (o)-[:FROM_DOCUMENT]->(d:Document)
RETURN o.id AS id, o.code AS code, o.raw_value AS raw_value, o.value AS value,
       o.unit AS unit, o.reference_range AS reference_range,
       o.interpretation AS interpretation, o.effective AS effective, d.id AS document_id
ORDER BY o.effective
"""

_MEDICATION_QUERY = """
MATCH (:Patient {id: $patient_id})-[:HAS_MEDICATION]->(m:Medication)
OPTIONAL MATCH (m)-[:FROM_DOCUMENT]->(d:Document)
RETURN m.id AS id, m.code AS code, m.dosage AS dosage, m.frequency AS frequency,
       m.status AS status, m.effective AS effective, d.id AS document_id
ORDER BY m.effective
"""

_CONDITION_QUERY = """
MATCH (:Patient {id: $patient_id})-[:HAS_CONDITION]->(c:Condition)
OPTIONAL MATCH (c)-[:FROM_DOCUMENT]->(d:Document)
RETURN c.id AS id, c.code AS code, c.status AS status, c.effective AS effective, d.id AS document_id
ORDER BY c.effective
"""


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _observation_row_to_read(row: dict) -> ObservationRead:
    return ObservationRead(
        id=row["id"],
        document_id=row.get("document_id"),
        type=ObservationType.LAB,
        name=row["code"],
        value=row.get("raw_value"),
        value_numeric=row.get("value"),
        unit=row.get("unit"),
        reference_range=row.get("reference_range"),
        interpretation=row.get("interpretation"),
        observed_date=_parse_date(row.get("effective")),
    )


def _medication_row_to_read(row: dict) -> ObservationRead:
    return ObservationRead(
        id=row["id"],
        document_id=row.get("document_id"),
        type=ObservationType.MEDICATION,
        name=row["code"],
        value=" ".join(filter(None, [row.get("dosage"), row.get("frequency")])) or None,
        status=row.get("status"),
        observed_date=_parse_date(row.get("effective")),
    )


def _condition_row_to_read(row: dict) -> ObservationRead:
    return ObservationRead(
        id=row["id"],
        document_id=row.get("document_id"),
        type=ObservationType.CONDITION,
        name=row["code"],
        status=row.get("status"),
        observed_date=_parse_date(row.get("effective")),
    )


def list_observations(
    observation_type: ObservationType | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ObservationRead]:
    """All stored patient facts, optionally filtered by type and/or date range.

    SYMPTOM/VITAL have no dedicated node label in ml/graph's schema today
    (everything numeric is an :Observation) -- filtering to either
    currently returns an empty list rather than raising, since it's a
    real (documented) gap, not a caller error.

    Date filtering happens here in Python, not in the Cypher queries --
    the graph's few-hundred-fact scale (see ml/graph/patient_context.py's
    own reasoning for the same choice) makes a round-trip param not worth
    the added query complexity.
    """
    with new_graph_client() as client:
        results: list[ObservationRead] = []
        if observation_type in (None, ObservationType.LAB):
            results += [_observation_row_to_read(row) for row in client.run(_OBSERVATION_QUERY, patient_id="self")]
        if observation_type in (None, ObservationType.MEDICATION):
            results += [_medication_row_to_read(row) for row in client.run(_MEDICATION_QUERY, patient_id="self")]
        if observation_type in (None, ObservationType.CONDITION):
            results += [_condition_row_to_read(row) for row in client.run(_CONDITION_QUERY, patient_id="self")]

    if start_date is not None:
        results = [o for o in results if o.observed_date is not None and o.observed_date >= start_date]
    if end_date is not None:
        results = [o for o in results if o.observed_date is not None and o.observed_date <= end_date]
    results.sort(key=lambda o: o.observed_date or date.min, reverse=True)
    return results


def build_timeline() -> TimelineResponse:
    """Group every numeric Observation into a per-metric chronological series.

    Labs/vitals only (medications/conditions are state, not a value
    series to plot) -- matches ml/graph/patient_context.get_trend_facts'
    same numeric-only scope.
    """
    with new_graph_client() as client:
        rows = client.run(_OBSERVATION_QUERY, patient_id="self")

    series_by_name: dict[str, TimelineSeries] = {}
    for row in rows:
        if row.get("effective") is None:
            continue
        series = series_by_name.setdefault(
            row["code"], TimelineSeries(name=row["code"], type=ObservationType.LAB, points=[])
        )
        series.points.append(
            TimelinePoint(
                observed_date=_parse_date(row["effective"]),
                value_numeric=row.get("value"),
                value=row.get("raw_value"),
                unit=row.get("unit"),
                observation_id=row["id"],
            )
        )

    return TimelineResponse(series=list(series_by_name.values()), generated_at=datetime.utcnow())
