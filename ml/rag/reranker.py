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

Chunk.metadata keys this module reads (degrades to a neutral score if
either is absent, so it works even for chunks that don't set them):
- "authority": float in [0, 1] (e.g. clinical guideline > peer-reviewed
  study > patient-reported note). Missing/out-of-range -> neutral 0.5.
- "published_date": ISO date string ("YYYY-MM-DD"). Missing/unparseable
  -> neutral 0.5 (no penalty for unknown age).

Structural fix for a known limitation (ml/rag/reranker_experiments/RESULTS.md):
MedCPT-Cross-Encoder saturates relevance near 1.0 for *any* chunk that's
topically on-subject — for "what was my LDL cholesterol result?",
seven-plus MedlinePlus chunks tied at exactly 1.000 simultaneously, not
one edge-case competitor. A weight sweep (current, two authority-boosted
configs, an authority-off baseline) confirmed raising AUTHORITY_WEIGHT
doesn't fix this and measurably hurts general-topic query accuracy — no
reasonable weight can outvote that many simultaneous ties. Instead of
tuning weights further, `rerank()` applies a patient-document floor: if
the best-matching patient-document chunk's own relevance score is within
PATIENT_FLOOR_RELEVANCE_MARGIN of the single best relevance score in the
candidate pool, it's promoted into top_k regardless of where pure
weighted scoring placed it — see ml/rag/reranker_experiments/RESULTS.md
for the empirical validation of this fix.
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

PATIENT_DOCUMENT_SOURCE = "patient_document"
# The observed gap between a genuinely relevant patient chunk (~0.92) and
# a saturated reference chunk (1.000) in the investigation that motivated
# this fix — see ml/rag/reranker_experiments/RESULTS.md. A margin this
# size promotes a patient chunk that's clearly relevant but shut out by
# ties, without forcing in a patient chunk that's actually unrelated to
# the query (a general-topic question with no personal answer).
PATIENT_FLOOR_RELEVANCE_MARGIN = 0.1


class Reranker:
    """Reorders retrieved chunks by relevance (cross-encoder) + authority + recency."""

    def __init__(
        self, model_name: str | None = None,
        relevance_weight: float = RELEVANCE_WEIGHT, authority_weight: float = AUTHORITY_WEIGHT,
        recency_weight: float = RECENCY_WEIGHT, enable_patient_floor: bool = True,
    ) -> None:
        self.model_name = model_name or os.environ.get("RERANKER_MODEL", DEFAULT_CROSS_ENCODER_MODEL)
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name).to(_DEVICE).eval()
        # Instance weights, not just the module constants directly -- lets
        # ml/rag/reranker_experiments/ compare configurations without
        # touching global state (see that experiment's RESULTS.md for why
        # this needed testing rather than a one-off constant change).
        self.relevance_weight = relevance_weight
        self.authority_weight = authority_weight
        self.recency_weight = recency_weight
        # Disableable for ml/rag/reranker_experiments/ to compare
        # weight-only vs. weight+floor behavior; production always wants
        # this on.
        self.enable_patient_floor = enable_patient_floor

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
        relevance_by_id = {chunk.id: relevance[i] for i, chunk in enumerate(chunks)}

        if top_k is not None:
            if self.enable_patient_floor:
                ranked = self._apply_patient_floor(ranked, relevance_by_id, top_k)
            return ranked[:top_k]
        return ranked

    def _apply_patient_floor(self, ranked: list[Chunk], relevance_by_id: dict[str, float], top_k: int) -> list[Chunk]:
        """Promote the best-matching patient-document chunk into top_k if ties otherwise excluded it.

        Only promotes when that chunk's own relevance is close to the
        pool's best (PATIENT_FLOOR_RELEVANCE_MARGIN) — a query with no
        real personal answer (e.g. "what causes chronic kidney disease")
        shouldn't have an unrelated patient-document chunk forced in just
        because one exists in the pool.
        """
        patient_chunks = [c for c in ranked if c.metadata.get("source") == PATIENT_DOCUMENT_SOURCE]
        if not patient_chunks or patient_chunks[0] in ranked[:top_k]:
            return ranked

        best_patient = patient_chunks[0]
        relevance_gap = relevance_by_id[ranked[0].id] - relevance_by_id[best_patient.id]
        if relevance_gap > PATIENT_FLOOR_RELEVANCE_MARGIN:
            return ranked

        promoted = [c for c in ranked if c is not best_patient]
        promoted.insert(top_k - 1, best_patient)
        return promoted

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
        """Weighted sum of relevance, authority, and recency (see instance weights)."""
        return (
            self.relevance_weight * relevance_score
            + self.authority_weight * self._authority_score(chunk)
            + self.recency_weight * self._recency_score(chunk)
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
