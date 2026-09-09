"""
Builds and writes typed Condition records to Neo4j, from
Lift VLM structured visual extraction (or legacy text extraction).

Schema:
    (:Patient {id})-[:HAS_CONDITION]->(:Condition)-[:FROM_DOCUMENT]->(:Document)

Condition is its own node type, not folded into Observation — a
diagnosis has a status (active/resolved/historical), not a value/unit
(see docs/GRAPH_SCHEMA_ROADMAP.md section 3e).
"""

from ml.graph.client import GraphClient
from ml.graph.document_dates import find_document_date
from ml.graph.observations import DEFAULT_PATIENT_ID


def build_conditions(
    conditions: list[dict], document_text: str, document_id: str, effective_date: str | None = None,
) -> list[dict]:
    """Attach a stable id + effective date to raw condition dicts from structured extraction.

    Pass effective_date to skip re-scanning document_text for a date if
    the caller already extracted it (see observations.build_table_observations'
    docstring for why).
    """
    effective = effective_date if effective_date is not None else find_document_date(document_text)
    result = []
    for condition in conditions:
        name = condition.get("name")
        if not name:
            continue
        result.append({
            "id": f"{document_id}:{name.lower().replace(' ', '_')}",
            "code": name,
            "status": condition.get("status") or "unspecified",
            "effective": effective,
        })
    return result


def write_conditions(
    client: GraphClient, document_id: str, filename: str, conditions: list[dict],
    patient_id: str = DEFAULT_PATIENT_ID,
) -> None:
    """Write parsed conditions to Neo4j, linked to a Patient and a Document node."""
    if not conditions:
        return
    client.run(
        """
        MERGE (p:Patient {id: $patient_id})
        MERGE (d:Document {id: $document_id})
        SET d.filename = $filename
        WITH p, d
        UNWIND $conditions AS cond
        MERGE (c:Condition {id: cond.id})
        SET c.code = cond.code, c.status = cond.status, c.effective = cond.effective
        MERGE (p)-[:HAS_CONDITION]->(c)
        MERGE (c)-[:FROM_DOCUMENT]->(d)
        """,
        patient_id=patient_id, document_id=document_id, filename=filename, conditions=conditions,
    )
