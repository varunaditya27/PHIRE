"""
POST /api/claims/extract — claim extraction endpoint (per CONTRIBUTING.md's
endpoint list).

Thin passthrough into ml.claims.extractor.ClaimExtractor.extract().
Typically called internally by router_chat.py's pipeline rather than
directly by the frontend, but exposed standalone for debugging/evaluation.
Returns unverified claim strings only -- no status/confidence, since
extraction and verification are separate ml/ steps (see
POST /api/evidence/verify for the latter).
"""

from fastapi import APIRouter

from app.models.claim import Claim, ClaimExtractRequest, ClaimExtractResponse
from app.utils.constants import EvidenceStatus
from app.services.gpu_modes import CHAT, gpu_mode
from app.services.ml_singletons import get_claim_extractor

router = APIRouter(prefix="/api/claims", tags=["claims"])


@router.post("/extract", response_model=ClaimExtractResponse)
def extract_claims(request: ClaimExtractRequest) -> ClaimExtractResponse:
    # gpu_mode(CHAT): see gpu_modes.py + ml_singletons.py's docstring -- get_claim_extractor()
    # makes an Ollama call, same GPU-shared resource as chat generation
    # and document ingestion.
    with gpu_mode(CHAT):
        statements = get_claim_extractor().extract(request.text)
    # UNCERTAIN, not a real verdict: extraction alone doesn't verify a
    # claim against evidence -- see POST /api/evidence/verify for a status
    # that means something.
    claims = [Claim(statement=s, status=EvidenceStatus.UNCERTAIN) for s in statements]
    return ClaimExtractResponse(claims=claims)
