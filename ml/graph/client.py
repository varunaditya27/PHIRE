"""
Thin wrapper around the Neo4j Python driver.

Local dev instance (not managed by this code — see ml/.env.example for
the exact command): a standalone podman/docker container, not yet part of
Anika's docker-compose.yml. Enforces localhost-only for the same reason
ml/llm/ollama_client.py does — PHIRE's local-only boundary shouldn't
depend on every caller remembering not to point this at a remote host.
"""

import os

from neo4j import Driver, GraphDatabase

from ml.local_only import require_localhost

DEFAULT_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
DEFAULT_USER = os.environ.get("NEO4J_USER", "neo4j")
DEFAULT_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")


class GraphClient:
    """Manages one Neo4j driver connection to the local Longitudinal Health Graph."""

    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None) -> None:
        self.uri = uri or DEFAULT_URI
        require_localhost(self.uri)
        self._driver: Driver = GraphDatabase.driver(self.uri, auth=(user or DEFAULT_USER, password or DEFAULT_PASSWORD))

    def run(self, query: str, **params) -> list[dict]:
        """Run one Cypher query and return its records as plain dicts."""
        with self._driver.session() as session:
            return [record.data() for record in session.run(query, **params)]

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> "GraphClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
