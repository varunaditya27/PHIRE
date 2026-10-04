"""
Shared Chunk -> EvidenceCitation conversion.

Used by both GET /api/search/evidence and POST /api/evidence/retrieve --
same underlying ml.rag.retriever.HybridRetriever.retrieve() call exposed
via two route shapes (query params vs. request body, per CONTRIBUTING.md's
original endpoint list), so the result-shaping logic shouldn't be
duplicated between them.
"""

from typing import TYPE_CHECKING

from app.models.response import EvidenceCitation

if TYPE_CHECKING:
    # Import-time only -- ml/rag/retriever.Chunk shouldn't be a hard
    # runtime import here (same reasoning as ml_singletons.py's module
    # docstring: this module must stay importable even when ml/'s deps
    # aren't installed).
    from ml.rag.retriever import Chunk


def chunk_to_citation(chunk: "Chunk", score: float | None = None) -> EvidenceCitation:
    return EvidenceCitation(
        evidence_passage_id=chunk.id,
        document_id=chunk.metadata.get("document_id"),
        text=chunk.text,
        source_url=chunk.metadata.get("url"),
        source_filename=chunk.metadata.get("filename"),
        authority=chunk.metadata.get("authority"),
        page_number=chunk.metadata.get("page_number"),
        score=score,
    )
