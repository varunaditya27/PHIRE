"""
Builds and writes typed Medication records to Neo4j, from
prose_extraction.py's LLM-based extraction.

Schema:
    (:Patient {id})-[:HAS_MEDICATION]->(:Medication)-[:FROM_DOCUMENT]->(:Document)

Medication is its own node type, not folded into Observation — dosage/
frequency/status are meaningfully different fields than an Observation's
value/unit/reference_range (see docs/GRAPH_SCHEMA_ROADMAP.md section 3e).
"""

from ml.graph.client import GraphClient
from ml.graph.observations import DEFAULT_PATIENT_ID, find_document_date


def build_medications(
    medications: list[dict], document_text: str, document_id: str, effective_date: str | None = None,
) -> list[dict]:
    """Attach a stable id + effective date to raw medication dicts from prose_extraction.extract_facts.

    Pass effective_date to skip re-scanning document_text for a date if
    the caller already extracted it (see observations.build_table_observations'
    docstring for why).
    """
    effective = effective_date if effective_date is not None else find_document_date(document_text)
    result = []
    for med in medications:
        name = med.get("name")
        if not name:
            continue
        result.append({
            "id": f"{document_id}:{name.lower().replace(' ', '_')}",
            "code": name,
            "dosage": med.get("dosage") or None,
            "frequency": med.get("frequency") or None,
            "status": med.get("status") or "unspecified",
            "effective": effective,
        })
    return result


def write_medications(
    client: GraphClient, document_id: str, filename: str, medications: list[dict],
    patient_id: str = DEFAULT_PATIENT_ID,
) -> None:
    """Write parsed medications to Neo4j, linked to a Patient and a Document node."""
    if not medications:
        return
    client.run(
        """
        MERGE (p:Patient {id: $patient_id})
        MERGE (d:Document {id: $document_id})
        SET d.filename = $filename
        WITH p, d
        UNWIND $medications AS med
        MERGE (m:Medication {id: med.id})
        SET m.code = med.code, m.dosage = med.dosage, m.frequency = med.frequency,
            m.status = med.status, m.effective = med.effective
        MERGE (p)-[:HAS_MEDICATION]->(m)
        MERGE (m)-[:FROM_DOCUMENT]->(d)
        """,
        patient_id=patient_id, document_id=document_id, filename=filename, medications=medications,
    )
