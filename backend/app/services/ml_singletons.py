"""
Shared, process-wide instances of ml/'s heavy classes.

ml.chains.qa_chain.QAChain, ml.rag.retriever.HybridRetriever,
ml.claims.verifier.ClaimVerifier, etc. each load real models on
construction (MedCPT embeddings, BART-large-MNLI, a Neo4j driver
connection) -- ml/README.md's handoff notes this is ~2-3GB of VRAM/RAM
and explicitly warns against constructing QAChain per-request. Every
router that needs ml/ pulls its client from here instead of constructing
its own, so the app holds exactly one of each across all requests.

Lazy + cached (@lru_cache), not built at import time: importing this
module must stay cheap (routers import it even when ml/'s heavy deps
aren't installed, e.g. in a lightweight test environment) -- the actual
model loads only happen the first time a route calls one of these
functions, and every call after that reuses the same instance.

All constructor args are passed explicitly from Settings rather than
relying on ml/'s internal os.environ.get(...) fallbacks -- pydantic-settings
loads backend/.env into Settings, not into the process's real os.environ,
so an ml/ class reading os.environ directly (e.g. HybridRetriever's
CHROMA_PERSIST_DIR) would silently miss it unless we thread the value
through explicitly here.
"""

import threading
from functools import lru_cache
from pathlib import Path

from app.config import get_settings

# Serializes GPU-heavy operations across requests: document ingestion
# (Ollama prose extraction, then MedCPT embedding via get_retriever()) and
# chat generation (Ollama generate, then MedCPT retrieval + BART-MNLI
# verification) can each independently OOM an 8GB GPU if they run
# concurrently, since get_retriever()'s embedding model stays VRAM-resident
# for the process's life once loaded (see this module's docstring) -- there
# is no way to guarantee ingestion finishes and releases its Ollama calls
# before a chat request loads the embedding model, or vice versa, without
# forcing the two to not overlap. A single process-wide lock is the
# documented mitigation in docs/BACKEND_HANDOFF.md's "VRAM ordering risk"
# known gap; acquired by every route that touches a GPU-resident
# singleton -- router_chat.py's chat(), document_processor.py's
# process_document(), router_evidence.py's /retrieve + /verify,
# router_search.py's /evidence, and router_claims.py's /extract (found
# via review: the first pass only covered chat+ingestion, missing these
# four) -- all of which run on worker threads (FastAPI's threadpool for
# sync routes, BackgroundTasks' worker thread for _run_processing), so
# blocking here doesn't block the event loop, only serializes these call
# sites against each other.
GPU_LOCK = threading.Lock()


@lru_cache
def get_lift_extractor():
    from ml.rag.ingest.lift_extractor import LiftExtractor

    settings = get_settings()
    return LiftExtractor(model_id=settings.lift_model)


@lru_cache
def get_retriever():
    from ml.rag.retriever import HybridRetriever

    settings = get_settings()
    return HybridRetriever(persist_dir=Path(settings.chroma_persist_dir))


@lru_cache
def get_reranker():
    from ml.rag.reranker import Reranker

    return Reranker()


@lru_cache
def get_ollama_client():
    from ml.llm.ollama_client import OllamaClient

    settings = get_settings()
    return OllamaClient(model=settings.ollama_model, host=settings.ollama_host)


@lru_cache
def get_claim_extractor():
    from ml.claims.extractor import ClaimExtractor

    return ClaimExtractor(client=get_ollama_client())


@lru_cache
def get_claim_verifier():
    from ml.claims.verifier import ClaimVerifier

    return ClaimVerifier()


def new_graph_client():
    """A fresh GraphClient (not cached -- it's a context manager most
    callers use with `with`, and the underlying Neo4j driver is cheap to
    open/close per call, unlike the model-loading singletons above)."""
    from ml.graph.client import GraphClient

    settings = get_settings()
    return GraphClient(uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password)


@lru_cache
def get_qa_chain():
    from ml.chains.qa_chain import QAChain

    return QAChain(
        retriever=get_retriever(),
        reranker=get_reranker(),
        extractor=get_claim_extractor(),
        verifier=get_claim_verifier(),
        llm_client=get_ollama_client(),
        graph_client=new_graph_client(),
    )
