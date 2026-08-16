"""
End-to-end QA pipeline: question -> retrieve -> rerank -> generate ->
extract claims -> verify -> confidence-score -> abstain-if-unsupported ->
response.

Orchestrates ml/rag, ml/llm, and ml/claims into the single pipeline
backing POST /api/chat. This is the "reverse RAG" flow: the LLM's draft
answer is decomposed into atomic claims, and the response actually shown
to the user is built only from claims that passed verification — an
unsupported/conflicting claim is dropped rather than surfaced as fact.

v1 composes the final answer by joining verified claim sentences, not by
asking the LLM to rewrite a clean answer from only the supported claims —
simpler and stays strictly within "only verified content is shown," at
the cost of prose that reads as a list of statements rather than a
flowing answer. Revisit once this is validated end-to-end.
"""

from dataclasses import dataclass

from ml.claims.confidence import compute_confidence
from ml.claims.extractor import ClaimExtractor
from ml.claims.verifier import ClaimVerifier
from ml.llm.ollama_client import OllamaClient
from ml.llm.prompt_builder import build_chat_prompt
from ml.rag.reranker import Reranker
from ml.rag.retriever import Chunk, HybridRetriever

# Claims below this confidence are treated as not-verified-enough to show
# as fact — tuned loosely (compute_confidence's own weights carry the real
# calibration); revisit once this runs against real chat traffic.
ABSTENTION_THRESHOLD = 0.4
NO_EVIDENCE_MESSAGE = "I don't have enough verified evidence to answer this confidently. Please consult a healthcare professional."


@dataclass
class VerifiedClaim:
    """One claim from the draft answer, its verification status, confidence, and cited source.

    source_span is the exact (start, end) character offset within the
    source document the evidence chunk came from — enables highlighting
    precisely what was cited, not just linking to the whole document. Not
    every chunk has one (table-row-derived and USDA chunks are
    reformatted, not extracted verbatim — see
    ml/rag/ingest/chunking.py's locate_chunk_offsets); None in that case,
    not a wrong guess.
    """

    claim: str
    status: str
    confidence: float
    source_url: str | None
    source_filename: str | None
    source_span: tuple[int, int] | None


@dataclass
class ChatResponse:
    """Final answer (built only from verified claims) plus the full claim-level audit trail."""

    answer: str
    claims: list[VerifiedClaim]


class QAChain:
    """Wires retrieval, reranking, generation, extraction, and verification into one call."""

    def __init__(
        self,
        retriever: HybridRetriever | None = None,
        reranker: Reranker | None = None,
        extractor: ClaimExtractor | None = None,
        verifier: ClaimVerifier | None = None,
        llm_client: OllamaClient | None = None,
    ) -> None:
        self._retriever = retriever or HybridRetriever()
        self._reranker = reranker or Reranker()
        self._extractor = extractor or ClaimExtractor()
        self._verifier = verifier or ClaimVerifier()
        self._llm = llm_client or OllamaClient()

    def answer(self, question: str, observations: list[str] | None = None, top_k: int = 5) -> ChatResponse:
        """Run the full retrieve -> generate -> verify -> abstain pipeline for one question."""
        # Wide candidate pool before reranking, not just top_k*2: a
        # specific patient fact (one line, narrow match) competes against
        # hundreds of topically-similar general reference chunks on pure
        # BM25/semantic similarity alone and can lose that contest despite
        # being the authoritative answer — reranker.py's authority
        # weighting only gets a chance to promote it if it survives into
        # the candidate pool in the first place. Verified live: a patient
        # document's own lab value ranked outside a top_k*2=10 pool but
        # inside a wider one.
        candidates = self._retriever.retrieve(question, top_k=max(20, top_k * 4))
        evidence = self._reranker.rerank(question, candidates, top_k=top_k)

        prompt = build_chat_prompt(question, evidence, observations)
        draft_answer = self._llm.generate(prompt)

        verified = [self._verify_claim(claim, evidence) for claim in self._extractor.extract(draft_answer)]
        supported = [c for c in verified if c.status == "SUPPORTED" and c.confidence >= ABSTENTION_THRESHOLD]
        answer = " ".join(c.claim for c in supported) if supported else NO_EVIDENCE_MESSAGE
        return ChatResponse(answer=answer, claims=verified)

    def _verify_claim(self, claim: str, evidence: list[Chunk]) -> VerifiedClaim:
        """Verify one claim and fold its verdict into a confidence score + source citation."""
        verification = self._verifier.verify(claim, evidence)
        rank = next((i for i, c in enumerate(evidence) if verification.evidence and c.id == verification.evidence.id), len(evidence))
        metadata = verification.evidence.metadata if verification.evidence else {}
        authority = metadata.get("authority", 0.0)
        confidence = compute_confidence(verification.entailment_prob, verification.contradiction_prob, rank, authority)
        source_span = None
        if "char_start" in metadata and "char_end" in metadata:
            source_span = (metadata["char_start"], metadata["char_end"])
        return VerifiedClaim(
            claim=claim, status=verification.status, confidence=confidence,
            source_url=metadata.get("url"), source_filename=metadata.get("filename"), source_span=source_span,
        )
