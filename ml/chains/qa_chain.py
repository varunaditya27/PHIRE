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

from collections.abc import Callable
from dataclasses import dataclass, field

from ml.claims.confidence import compute_confidence
from ml.claims.extractor import ClaimExtractor
from ml.claims.verifier import ClaimVerifier
from ml.graph.client import GraphClient
from ml.graph.patient_context import get_current_patient_facts_with_sources, get_patient_facts, get_trend_facts
from ml.llm.ollama_client import OllamaClient
from ml.llm.prompt_builder import build_chat_prompt
from ml.rag.reranker import Reranker
from ml.rag.retriever import Chunk, HybridRetriever

# Claims below this confidence are treated as not-verified-enough to show
# as fact — tuned loosely (compute_confidence's own weights carry the real
# calibration); revisit once this runs against real chat traffic.
ABSTENTION_THRESHOLD = 0.4
NO_EVIDENCE_MESSAGE = "I don't have enough verified evidence to answer this confidently. Please consult a healthcare professional."

# Hard ceiling on how many patient/trend facts enter the verification
# pool. ClaimVerifier.verify() runs a full BART-large-MNLI forward pass
# per (claim, pool-chunk) pair (see ml/claims/verifier.py) — with no cap,
# a patient tracked across dozens of metrics over years turns into
# O(claims x entire-history) NLI calls on every chat turn (found via
# review, not hypothetical yet: get_current_patient_facts already
# collapses to one row per metric and get_trend_facts to one row per
# multi-reading metric, so this doesn't bite at today's few-fact scale,
# but has no backstop once real longitudinal data accumulates). Applied
# separately to patient facts and trend facts so one list can't crowd out
# the other; kept generous (not a tight top-k) since, unlike the
# retrieval candidate pool, there's no cheap relevance score to rank
# these by before NLI runs.
MAX_FACT_EVIDENCE = 50


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
    # The reranked passages the answer was drafted from, for the API's `citations`.
    evidence: list[Chunk] = field(default_factory=list)


class QAChain:
    """Wires retrieval, reranking, generation, extraction, and verification into one call."""

    def __init__(
        self,
        retriever: HybridRetriever | None = None,
        reranker: Reranker | None = None,
        extractor: ClaimExtractor | None = None,
        verifier: ClaimVerifier | None = None,
        llm_client: OllamaClient | None = None,
        graph_client: GraphClient | None = None,
    ) -> None:
        self._retriever = retriever or HybridRetriever()
        self._reranker = reranker or Reranker()
        self._extractor = extractor or ClaimExtractor()
        self._verifier = verifier or ClaimVerifier()
        self._llm = llm_client or OllamaClient()
        self._graph_client = graph_client or GraphClient()

    def answer(
        self,
        question: str,
        observations: list[str] | None = None,
        top_k: int = 5,
        on_progress: Callable[[str, str], None] | None = None,
    ) -> ChatResponse:
        """Run the full retrieve -> generate -> verify -> abstain pipeline for one question.

        observations defaults to the patient's current graph state
        (ml/graph/patient_context.py) -- callers only need to pass it
        explicitly to override that default (e.g. tests).

        on_progress(stage, message), if given, is called as each stage
        starts so a caller (the backend's SSE endpoint) can show what the
        slow, otherwise-silent pipeline is doing; it never affects results.
        """
        progress = on_progress or (lambda stage, message: None)
        progress("graph", "Reading your health records")
        history_facts, current_facts, trend_facts = self._graph_facts(need_history=observations is None)
        if observations is None:
            observations = history_facts + trend_facts

        # Wide candidate pool before reranking, not just top_k*2: a
        # specific patient fact (one line, narrow match) competes against
        # hundreds of topically-similar general reference chunks on pure
        # BM25/semantic similarity alone and can lose that contest despite
        # being the authoritative answer — reranker.py's authority
        # weighting only gets a chance to promote it if it survives into
        # the candidate pool in the first place. Verified live: a patient
        # document's own lab value ranked outside a top_k*2=10 pool but
        # inside a wider one.
        progress("retrieve", "Searching medical evidence")
        candidates = self._retriever.retrieve(question, top_k=max(20, top_k * 4))
        evidence = self._reranker.rerank(question, candidates, top_k=top_k)

        prompt = build_chat_prompt(question, evidence, observations)
        progress("generate", "Drafting an answer with the local model")
        draft_answer = self._llm.generate(prompt)

        # A claim restating a patient fact ("your LDL was 162 mg/dL") needs
        # to be checked against that fact, not just against reference
        # literature -- without this, a claim built entirely from
        # observations always came back UNCERTAIN, since no chunk in
        # evidence could ever entail it (verified live: this is what
        # actually happened before this fix). Uses get_current_patient_facts
        # (latest value per metric), not the full-history `observations`
        # list used for the prompt above -- checking against every past
        # value of a metric makes NLI flag an old reading as contradicting
        # a new one (also verified live). Listed first so a patient fact
        # wins ties over a topically-similar reference chunk when both
        # score similarly informative.
        patient_evidence = self._facts_to_chunks(
            [fact for fact, _ in current_facts], source="patient_record", filenames=[name for _, name in current_facts],
        )
        # A trend claim ("your LDL increased 29 points") is arithmetic on
        # two Observations, not something NLI can verify against a single
        # fact sentence -- get_trend_facts precomputes the delta as its
        # own checkable sentence, tagged patient_derived so _verify_claim
        # can relabel a match here as DERIVED rather than SUPPORTED (see
        # ml/claims/verifier.py's docstring for why DERIVED can't be
        # implemented as an NLI-only distinction).
        derived_evidence = self._facts_to_chunks(trend_facts, source="patient_derived")
        verification_pool = patient_evidence + derived_evidence + evidence

        progress("extract", "Splitting the draft into checkable claims")
        claims = self._extractor.extract(draft_answer)
        verified = []
        for i, claim in enumerate(claims, start=1):
            progress("verify", f"Verifying claim {i} of {len(claims)} against your records and evidence")
            verified.append(self._verify_claim(claim, verification_pool))
        supported = [c for c in verified if c.status in ("SUPPORTED", "DERIVED") and c.confidence >= ABSTENTION_THRESHOLD]
        answer = " ".join(c.claim for c in supported) if supported else NO_EVIDENCE_MESSAGE
        return ChatResponse(answer=answer, claims=verified, evidence=evidence)

    def _graph_facts(
        self, need_history: bool,
    ) -> tuple[list[str], list[tuple[str, str | None]], list[str]]:
        """(history facts, (current fact, source filename) pairs, trend facts) from the graph, or three empty
        lists if Neo4j is unreachable.

        The graph layer is documented (CLAUDE.md) as "not MVP-blocking" --
        a general question with no patient-specific content shouldn't
        502 the whole request just because Neo4j is down; it should just
        lose the patient-specific/trend grounding for that turn. Fetched
        together in one try/except (not one per call site) so a partial
        graph outage can't leave observations/current_facts/trend_facts
        in an inconsistent mix of real and empty. get_trend_facts is only
        computed once, reused for both the prompt-context `observations`
        and the trend-claim verification pool below, instead of querying
        the graph for the identical result twice.
        """
        history_facts: list[str] = []
        try:
            if need_history:
                history_facts = get_patient_facts(self._graph_client)
            current_facts = get_current_patient_facts_with_sources(self._graph_client)
            trend_facts = get_trend_facts(self._graph_client)
        except Exception as exc:  # noqa: BLE001 -- degrade, not crash; see docstring
            print(f"QAChain: graph unavailable, answering without patient-graph facts: {exc}")
            return [], [], []
        return history_facts, current_facts, trend_facts

    @staticmethod
    def _facts_to_chunks(facts: list[str], source: str, filenames: list[str | None] | None = None) -> list[Chunk]:
        """Wrap plain-text graph facts as Chunks so the verifier can check claims against them.

        authority=1.0 matches PATIENT_DOCUMENT_AUTHORITY (reranker.py) --
        a structured graph fact is at least as authoritative as the raw
        document chunk it was extracted from. source is carried through
        in metadata so _verify_claim can tell a direct patient fact apart
        from a precomputed trend when labeling the final status.

        Truncated to MAX_FACT_EVIDENCE (see its own comment for why) --
        logged rather than silently dropped, since a truncated fact is a
        fact this pool can no longer verify a claim against.
        """
        if len(facts) > MAX_FACT_EVIDENCE:
            print(f"QAChain: capping {len(facts)} {source} facts to {MAX_FACT_EVIDENCE} for claim verification")
            facts = facts[:MAX_FACT_EVIDENCE]
        filenames = filenames or [None] * len(facts)
        return [
            Chunk(
                id=f"{source}_{i}", text=fact,
                # filename lets a verified claim cite which uploaded document the fact came from.
                metadata={"source": source, "authority": 1.0, **({"filename": name} if name else {})},
            )
            for i, (fact, name) in enumerate(zip(facts, filenames))
        ]

    def _verify_claim(self, claim: str, evidence: list[Chunk]) -> VerifiedClaim:
        """Verify one claim and fold its verdict into a confidence score + source citation."""
        verification = self._verifier.verify(claim, evidence)
        if verification.evidence is None:
            # No matched chunk (empty verification pool -- see
            # ClaimVerifier.verify()'s docstring) means literally no
            # evidence to base a rank/authority-weighted confidence on.
            # `next(..., len(evidence))`'s old fallback collided with a
            # real rank of 0 when evidence was empty (len([])==0), giving
            # a zero-evidence claim compute_confidence's retrieval-only
            # floor (0.25) instead of ~0 -- found via review.
            metadata: dict = {}
            confidence = 0.0
        else:
            rank = next(i for i, c in enumerate(evidence) if c.id == verification.evidence.id)
            metadata = verification.evidence.metadata
            authority = metadata.get("authority", 0.0)
            confidence = compute_confidence(verification.entailment_prob, verification.contradiction_prob, rank, authority)
        status = verification.status
        # A SUPPORTED match against a patient_derived chunk means the
        # claim restated a precomputed trend (arithmetic PHIRE already
        # did), not a direct fact or reference-backed statement -- relabel
        # so the caller can distinguish "this is a computed delta" from
        # "this is a directly observed value" (docs/PHIRE_STRUCTURED_GRAPH_MEDICAL_CORPUS_IMPLEMENTATION.md
        # section 33's DIRECT FACT vs DERIVED distinction).
        if status == "SUPPORTED" and metadata.get("source") == "patient_derived":
            status = "DERIVED"
        source_span = None
        if "char_start" in metadata and "char_end" in metadata:
            source_span = (metadata["char_start"], metadata["char_end"])
        return VerifiedClaim(
            claim=claim, status=status, confidence=confidence,
            source_url=metadata.get("url"), source_filename=metadata.get("filename"), source_span=source_span,
        )
