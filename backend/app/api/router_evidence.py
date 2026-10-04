"""
POST /api/evidence/retrieve, POST /api/evidence/verify — evidence pipeline
endpoints (per CONTRIBUTING.md's endpoint list).

Thin passthroughs into ml.rag.retriever.HybridRetriever.retrieve() and
ml.claims.verifier.ClaimVerifier.verify() -- business logic stays in
ml/, not here. Both instances are shared singletons (see
app/services/ml_singletons.py).

/verify takes the claim text plus the evidence to check it against by
value (the actual retrieved passages, typically from a prior /retrieve
call), not evidence_passage_ids -- ml/'s Chunk objects are keyed by
source-derived string ids with no backend database row behind them, so
there's nothing a UUID could look up.
"""

from fastapi import APIRouter

from ml.claims.confidence import compute_confidence

from app.models.claim import Claim
from app.models.response import (
    EvidenceRetrieveRequest,
    EvidenceRetrieveResponse,
    EvidenceVerifyRequest,
    EvidenceVerifyResponse,
)
from app.services.evidence_search import search_evidence
from app.services.gpu_modes import CHAT, gpu_mode
from app.services.ml_singletons import get_claim_verifier, get_retriever

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.post("/retrieve", response_model=EvidenceRetrieveResponse)
def retrieve_evidence(request: EvidenceRetrieveRequest) -> EvidenceRetrieveResponse:
    return EvidenceRetrieveResponse(citations=search_evidence(request.query, request.top_k))


@router.post("/verify", response_model=EvidenceVerifyResponse)
def verify_claim(request: EvidenceVerifyRequest) -> EvidenceVerifyResponse:
    # Re-retrieve using the claim text itself as the query: /verify's
    # request contract (per CONTRIBUTING.md) only carries the claim, not
    # the evidence to check it against, so this route has to find its own
    # candidate evidence rather than receiving it (contrast with
    # ml.chains.qa_chain.QAChain, which already has a reranked pool in
    # hand from the same turn's retrieval step).
    #
    # gpu_mode(CHAT): see gpu_modes.py + ml_singletons.py's docstring -- both retrieve() and
    # verify() below use GPU-resident models (MedCPT, BART-MNLI).
    with gpu_mode(CHAT):
        evidence = get_retriever().retrieve(request.claim, top_k=5)
        verification = get_claim_verifier().verify(request.claim, evidence)

    # Same confidence formula QAChain uses (ml/chains/qa_chain.py's
    # _verify_claim), including its no-evidence case: `next(..., len(evidence))`
    # collided with a real rank of 0 when evidence was empty, handing a
    # zero-evidence claim a spurious non-zero confidence (found via
    # review) -- verification.evidence is None is exactly that case.
    if verification.evidence is None:
        metadata: dict = {}
        confidence = 0.0
    else:
        metadata = verification.evidence.metadata
        rank = next(i for i, c in enumerate(evidence) if c.id == verification.evidence.id)
        authority = metadata.get("authority", 0.0)
        confidence = compute_confidence(verification.entailment_prob, verification.contradiction_prob, rank, authority)

    source_span = None
    if "char_start" in metadata and "char_end" in metadata:
        source_span = (metadata["char_start"], metadata["char_end"])

    claim = Claim(
        statement=verification.claim,
        status=verification.status,
        confidence=confidence,
        source_url=metadata.get("url"),
        source_filename=metadata.get("filename"),
        source_span=source_span,
    )
    return EvidenceVerifyResponse(claim=claim)
