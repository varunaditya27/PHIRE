"""
GET /api/observations, GET /api/timeline — structured health data endpoints.

Serves normalized observations/medications/conditions read live from
ml/graph's Neo4j Longitudinal Health Graph (see
app/services/graph_reader.py) -- PHIRE's actual source of structured
patient facts, populated by document ingestion
(ml.rag.ingest.ingest_patient_document, see app/services/document_processor.py).
No patient_id in the path: PHIRE is single-patient (see
app/database/schemas.py's module docstring).
"""

from datetime import date

from fastapi import APIRouter

from app.models.observation import ObservationRead, TimelineResponse
from app.services.graph_reader import build_timeline, list_observations
from app.utils.constants import ObservationType
from app.utils.validators import validate_date_range

router = APIRouter(prefix="/api", tags=["observations"])


@router.get("/observations", response_model=list[ObservationRead])
def get_observations(
    type: ObservationType | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ObservationRead]:
    validate_date_range(start_date, end_date)
    return list_observations(type, start_date, end_date)


@router.get("/timeline", response_model=TimelineResponse)
def get_timeline() -> TimelineResponse:
    return build_timeline()
