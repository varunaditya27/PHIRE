"""Unit test for ml/graph/client.py's localhost enforcement (no live Neo4j needed)."""

import pytest

from ml.graph.client import GraphClient


def test_graph_client_rejects_remote_uri():
    with pytest.raises(ValueError, match="localhost"):
        GraphClient(uri="bolt://some-remote-server.example.com:7687")
