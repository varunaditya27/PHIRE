"""Unit tests for backend/app/services/evidence_search.py: reranked results carry relevance as `score`."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_path = str(Path(__file__).resolve().parents[2] / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services import evidence_search
from ml.rag.retriever import Chunk


def test_search_returns_reranked_citations_with_cross_encoder_scores():
    a = Chunk(id="a", text="alpha", metadata={"filename": "labs.pdf", "authority": 1.0})
    b = Chunk(id="b", text="beta", metadata={"url": "https://example.org/b", "authority": 0.9})
    retriever, reranker = MagicMock(), MagicMock()
    retriever.retrieve.return_value = [b, a]
    reranker.rerank.return_value = [a, b]
    reranker.score.return_value = [0.91, 0.40]

    with patch.object(evidence_search, "get_retriever", return_value=retriever), patch.object(
        evidence_search, "get_reranker", return_value=reranker
    ), patch.object(evidence_search, "gpu_mode"):
        citations = evidence_search.search_evidence("ldl", top_k=2)

    retriever.retrieve.assert_called_once_with("ldl", top_k=20)  # wide pool, like chat
    reranker.rerank.assert_called_once_with("ldl", [b, a], top_k=2)
    assert [(c.evidence_passage_id, c.score) for c in citations] == [("a", 0.91), ("b", 0.40)]
    assert citations[0].source_filename == "labs.pdf"
    assert citations[1].source_url == "https://example.org/b"
