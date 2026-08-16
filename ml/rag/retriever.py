"""
Hybrid retrieval over ingested documents + trusted reference sources.

Retrieval is three-way, not two-way (finalized decision, see
docs/DATASETS_AND_GRAPH_RAG.md):
1. Lexical (BM25, via rank_bm25) — catches exact lab-value/term matches
   that embeddings can miss.
2. Semantic (dense embedding, Chroma in-process vector store) — catches
   paraphrase/similarity matches BM25 misses.
3. Graph traversal (LightRAG over a Neo4j-backed entity/relationship
   graph) — multi-hop/relational/contradiction questions. Planned for
   Month 2-3 per docs/AGGRESSIVE_ROADMAP.md — NOT implemented here yet.

This module currently implements legs 1 and 2, fused via reciprocal rank
fusion. ml/rag/reranker.py owns authority/recency-aware reranking on top of
this fused result — RRF here only combines two similarity-based rankings
fairly, it isn't a final relevance score.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

import chromadb
from rank_bm25 import BM25Okapi

from ml.rag.embeddings import EmbeddingModel

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHROMA_DIR = REPO_ROOT / "data" / "chroma"
COLLECTION_NAME = "phire_evidence"

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# BM25's IDF alone doesn't downweight these enough on a corpus this size
# (hundreds, not millions, of documents) — without filtering, a query
# like "should I worry about a mole on my skin?" ranks documents by
# incidental overlap on "should"/"a"/"on"/"my" ahead of documents that
# actually share its content words.
_STOPWORDS = frozenset("""
a about above after again against all am an and any are aren't as at be because been before being below between both but by can't cannot could
couldn't did didn't do does doesn't doing don't down during each few for from further had hadn't has hasn't have haven't having he he'd he'll
he's her here here's hers herself him himself his how how's i i'd i'll i'm i've if in into is isn't it it's its itself let's me more most
mustn't my myself no nor not of off on once only or other ought our ours ourselves out over own same shan't she she'd she'll she's should
shouldn't so some such than that that's the their theirs them themselves then there there's these they they'd they'll they're they've this those
through to too under until up very was wasn't we we'd we'll we're we've were weren't what what's when when's where where's which while who
who's whom why why's will with won't would wouldn't you you'd you'll you're you've your yours yourself yourselves
""".split())


def _tokenize(text: str) -> list[str]:
    """Lowercase, punctuation-stripped, stopword-filtered tokens for BM25.

    A plain .split() looked fine against short synthetic test strings but
    silently breaks BM25 on real ingested prose: "mole" (query) vs "mole,"
    or "Mole" (corpus, capitalized/punctuated) never match as the same
    token, so BM25 degenerates into scoring on whatever stray function
    words happen to line up instead of actual content terms.
    """
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


@dataclass
class Chunk:
    """One retrievable unit: a document/reference passage plus its metadata."""

    id: str
    text: str
    metadata: dict


class HybridRetriever:
    """Fuses BM25 (lexical) and Chroma (semantic) search via reciprocal rank fusion."""

    def __init__(
        self,
        embedding_model: EmbeddingModel | None = None,
        persist_dir: Path | None = None,
    ) -> None:
        # Resolved relative to the repo root, not cwd, so behavior doesn't
        # change depending on where the backend process is launched from.
        chroma_path = persist_dir or Path(os.environ.get("CHROMA_PERSIST_DIR", DEFAULT_CHROMA_DIR))
        self._embedder = embedding_model or EmbeddingModel()
        self._client = chromadb.PersistentClient(path=str(chroma_path))
        self._collection = self._client.get_or_create_collection(COLLECTION_NAME)
        self._chunks: dict[str, Chunk] = {}
        self._bm25: BM25Okapi | None = None
        self._bm25_ids: list[str] = []
        # Chroma persists embeddings across processes, but self._chunks and
        # the BM25 index only exist in memory — without this, a fresh
        # process (e.g. the backend querying data ingested by a separate
        # run_ingest.py invocation) would see an empty index despite Chroma
        # already holding the data.
        self._load_existing_chunks()

    def _load_existing_chunks(self) -> None:
        """Rehydrate self._chunks/BM25 from whatever Chroma already has on disk."""
        existing = self._collection.get(include=["documents", "metadatas"])
        if not existing["ids"]:
            return
        for cid, text, metadata in zip(existing["ids"], existing["documents"], existing["metadatas"]):
            self._chunks[cid] = Chunk(id=cid, text=text, metadata=dict(metadata))
        self._rebuild_bm25()

    def add_documents(self, chunks: list[Chunk]) -> None:
        """Index chunks into both the Chroma vector store and the BM25 lexical index."""
        if not chunks:
            return
        embeddings = self._embedder.embed_documents([c.text for c in chunks])
        # upsert, not add: add() silently no-ops on a duplicate id instead
        # of replacing its content, so re-ingesting an updated document
        # (same id, new text) would leave the stale version in Chroma
        # forever — verified live via patient-document re-ingestion.
        self._collection.upsert(
            ids=[c.id for c in chunks],
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            # Chroma rejects an empty metadata dict outright; fall back to
            # the chunk id so callers can pass metadata={} before ingestion
            # has authority/date info to attach.
            metadatas=[c.metadata or {"chunk_id": c.id} for c in chunks],
        )
        for c in chunks:
            self._chunks[c.id] = c
        self._rebuild_bm25()

    def _rebuild_bm25(self) -> None:
        """Recompute the BM25 index over all chunks seen so far.

        Rebuilt on every add rather than incrementally updated — BM25Okapi
        has no incremental-add API, and PHIRE's ingestion volume (tens to
        low hundreds of reference docs for MVP) makes a full rebuild cheap.
        """
        self._bm25_ids = list(self._chunks.keys())
        corpus = [_tokenize(self._chunks[cid].text) for cid in self._bm25_ids]
        self._bm25 = BM25Okapi(corpus)

    def retrieve(self, query: str, top_k: int = 5) -> list[Chunk]:
        """Return up to top_k chunks ranked by fused BM25 + Chroma relevance."""
        if not self._chunks:
            return []
        semantic_ids = self._semantic_search(query, top_k)
        lexical_ids = self._lexical_search(query, top_k)
        fused = self._reciprocal_rank_fusion([semantic_ids, lexical_ids])
        return [self._chunks[cid] for cid in fused[:top_k]]

    def _semantic_search(self, query: str, top_k: int) -> list[str]:
        """Chroma nearest-neighbor search, ranked ids only."""
        query_embedding = self._embedder.embed_query(query)
        result = self._collection.query(query_embeddings=[query_embedding], n_results=top_k)
        return result["ids"][0] if result["ids"] else []

    def _lexical_search(self, query: str, top_k: int) -> list[str]:
        """BM25 exact/near-exact term search, ranked ids only."""
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(self._bm25_ids, scores), key=lambda pair: pair[1], reverse=True)
        return [cid for cid, _ in ranked[:top_k]]

    @staticmethod
    def _reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[str]:
        """Merge multiple ranked id lists into one, favoring ids ranked highly in either."""
        scores: dict[str, float] = {}
        for ranked in ranked_lists:
            for rank, cid in enumerate(ranked):
                scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        return sorted(scores, key=scores.get, reverse=True)
