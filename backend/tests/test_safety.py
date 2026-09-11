# tests for PHIRE safety enhancements
import sys, os
sys.path.append(os.path.abspath('.'))

from ml.chains.qa_chain import QAChain, NO_EVIDENCE_MESSAGE, ChatResponse
from ml.rag.retriever import HybridRetriever
from ml.rag.reranker import Reranker
from ml.claims.verifier import ClaimVerifier
# Mock verifier that does nothing (won't be called due to early abort)
class MockVerifier:
    def verify(self, claim, evidence):
        return None


# Mock retriever that returns no candidates
class EmptyRetriever(HybridRetriever):
    def __init__(self, *args, **kwargs):
        # Bypass HybridRetriever.__init__ which loads heavy embeddings.
        pass

    def retrieve(self, query: str, top_k: int = 5):
        return []

# Mock reranker that returns no evidence
class EmptyReranker(Reranker):
    def rerank(self, query: str, candidates, top_k: int = 5):
        return []

def test_evidence_sufficiency_gate_returns_abstention():
    chain = QAChain(
        retriever=EmptyRetriever(),
        reranker=EmptyReranker(),
        extractor=None,
        verifier=MockVerifier(),
        llm_client=None,
        graph_client=None,
    )
    response = chain.answer("What is my LDL?", observations=None)
    assert isinstance(response, ChatResponse)
    assert response.answer == NO_EVIDENCE_MESSAGE
    assert response.claims == []

def test_claim_verifier_unsuppored_status():
    probs = {"entailment": 0.5, "contradiction": 0.4, "neutral": 0.1}
    status = ClaimVerifier._status_from_probs(probs)
    assert status == "UNSUPPORTED"
