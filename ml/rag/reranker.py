"""
Evidence reranking: relevance + authority + recency scoring.

Takes retriever.py's fused BM25/Chroma candidates and reorders them with a
signal RRF can't express on its own: a candidate's fusion rank says nothing
about whether its *content* actually answers the query, how authoritative
its source is, or whether it's stale. This module adds those three signals
on top of retrieval, per PHIRE's evidence-quality ranking research
question (docs/FEATURES_ALIGNED.md).

Model choice: ncbi/MedCPT-Cross-Encoder — third model in the MedCPT family
already adopted for embeddings (ml/rag/embeddings.py, see
ml/rag/experiments/RESULTS.md), so reranking stays consistent with that
decision instead of introducing an unrelated model.

Chunk.metadata has no fixed schema yet (document ingestion isn't built).
This module defines the two keys it reads and degrades to a neutral score
when either is absent, so it works before ingestion sets them and doesn't
silently misrank once it does:
- "authority": float in [0, 1] (e.g. clinical guideline > peer-reviewed
  study > patient-reported note). Missing/out-of-range -> neutral 0.5.
- "published_date": ISO date string ("YYYY-MM-DD"). Missing/unparseable
  -> neutral 0.5 (no penalty for unknown age).
"""

import os
from datetime import date, datetime

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from ml.rag.retriever import Chunk

DEFAULT_CROSS_ENCODER_MODEL = "ncbi/MedCPT-Cross-Encoder"
_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Relevance dominates (it's the only signal grounded in query content);
# authority and recency nudge the ordering among otherwise-similar matches.
RELEVANCE_WEIGHT = 0.6
AUTHORITY_WEIGHT = 0.25
RECENCY_WEIGHT = 0.15

# Recency score halves every ~2 years — chosen so multi-year-old guidance
# is still eligible to rank well (medical consensus moves slowly) but
# recent evidence gets a real, visible boost.
RECENCY_HALF_LIFE_DAYS = 730
_NEUTRAL_SCORE = 0.5


class Reranker:
    """Reorders retrieved chunks by relevance (cross-encoder) + authority + recency."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.environ.get("RERANKER_MODEL", DEFAULT_CROSS_ENCODER_MODEL)
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name).to(_DEVICE).eval()

    def rerank(self, query: str, chunks: list[Chunk], top_k: int | None = None) -> list[Chunk]:
        """Rescore chunks against the query and return them best-first (optionally truncated to top_k)."""
        if not chunks:
            return []
        relevance = self._relevance_scores(query, chunks)
        scored = [
            (chunk, self._combine(relevance[i], chunk))
            for i, chunk in enumerate(chunks)
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        ranked = [chunk for chunk, _ in scored]
        return ranked[:top_k] if top_k is not None else ranked

    def _relevance_scores(self, query: str, chunks: list[Chunk]) -> list[float]:
        """Cross-encoder relevance for each chunk, squashed to [0, 1] via sigmoid."""
        pairs = [[query, chunk.text] for chunk in chunks]
        with torch.no_grad():
            encoded = self._tokenizer(
                pairs, truncation=True, padding=True, return_tensors="pt", max_length=512
            ).to(_DEVICE)
            logits = self._model(**encoded).logits.squeeze(dim=1)
            return torch.sigmoid(logits).cpu().tolist()

    def _combine(self, relevance_score: float, chunk: Chunk) -> float:
        """Weighted sum of relevance, authority, and recency (see module-level weights)."""
        return (
            RELEVANCE_WEIGHT * relevance_score
            + AUTHORITY_WEIGHT * self._authority_score(chunk)
            + RECENCY_WEIGHT * self._recency_score(chunk)
        )

    @staticmethod
    def _authority_score(chunk: Chunk) -> float:
        """Source-authority signal from metadata; neutral if absent or malformed."""
        value = chunk.metadata.get("authority")
        if not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
            return _NEUTRAL_SCORE
        return float(value)

    @staticmethod
    def _recency_score(chunk: Chunk) -> float:
        """Exponential decay from published_date; neutral if absent or unparseable."""
        raw_date = chunk.metadata.get("published_date")
        if not isinstance(raw_date, str):
            return _NEUTRAL_SCORE
        try:
            published = date.fromisoformat(raw_date)
        except ValueError:
            return _NEUTRAL_SCORE
        age_days = max((datetime.now().date() - published).days, 0)
        return 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)
