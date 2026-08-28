"""
Deletes every graph fact written for one document.

Compensating action for a failed ingestion: observations.py/medications.py/
conditions.py all write their fact nodes as
(:Fact)-[:FROM_DOCUMENT]->(:Document {id: document_id}) (see each
module's own schema comment) — one generic Cypher query, driven by that
shared shape, covers all three fact types plus the Document node itself
without needing a per-fact-type delete.
"""

from ml.graph.client import GraphClient

_DELETE_DOCUMENT_FACTS_QUERY = """
MATCH (d:Document {id: $document_id})
OPTIONAL MATCH (n)-[:FROM_DOCUMENT]->(d)
DETACH DELETE n, d
"""


def delete_document_facts(client: GraphClient, document_id: str) -> None:
    """Remove every Observation/Medication/Condition (and the Document node itself)
    written for document_id. A no-op if nothing was ever written for it."""
    client.run(_DELETE_DOCUMENT_FACTS_QUERY, document_id=document_id)
