"""
Pydantic schemas for normalized health observations.

Observation: value, unit, date, reference range, source document. These
schemas are the contract behind GET /api/observations and
GET /api/timeline, backed by ml.graph's Neo4j Longitudinal Health Graph
(see app/services/graph_reader.py) -- not a backend-owned Postgres table.

id/document_id are str, not UUID: ml/graph's node ids are source-derived
strings (f"{document_id}:{code}", see ml/graph/observations.py's
_stable_id), and document_id is the same content-hash string
ml.rag.ingest.ingest_patient_document.build_chunks uses to key a
document's chunks -- neither is a database-generated UUID.
"""

from datetime import date, datetime

from pydantic import BaseModel

from app.utils.constants import ObservationType


class ObservationRead(BaseModel):
    id: str
    document_id: str | None = None
    type: ObservationType
    name: str
    value: str | None = None
    value_numeric: float | None = None
    unit: str | None = None
    reference_range: str | None = None
    interpretation: str | None = None
    status: str | None = None  # medication/condition status (e.g. "active", "continued") -- N/A for labs
    observed_date: date | None = None

    model_config = {"from_attributes": True}


class TimelinePoint(BaseModel):
    observed_date: date
    value_numeric: float | None = None
    value: str | None = None
    unit: str | None = None
    observation_id: str


class TimelineSeries(BaseModel):
    name: str
    type: ObservationType
    points: list[TimelinePoint]


class TimelineResponse(BaseModel):
    series: list[TimelineSeries]
    generated_at: datetime
