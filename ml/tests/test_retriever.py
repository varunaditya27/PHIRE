"""
Unit tests for ml/rag/retriever.py's BM25 + Chroma fusion logic.

Uses a fake embedding model (no network/model download) so these tests run
fast and don't depend on Hugging Face availability.
"""

from ml.rag.retriever import Chunk, HybridRetriever


class FakeEmbeddingModel:
    """Deterministic bag-of-words embedder standing in for PubMedBERT in tests.

    Real semantic search picks up paraphrases BM25 misses; this fake only
    needs to be consistent enough to prove the fusion plumbing works, not to
    be semantically meaningful.
    """

    VOCAB = ["ldl", "cholesterol", "glucose", "statin", "exercise"]

    def _vectorize(self, text: str) -> list[float]:
        words = text.lower().split()
        return [float(words.count(term)) for term in self.VOCAB]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vectorize(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vectorize(text)


def build_retriever(tmp_path) -> HybridRetriever:
    return HybridRetriever(embedding_model=FakeEmbeddingModel(), persist_dir=tmp_path / "chroma")


def test_retrieve_ranks_lexical_and_semantic_matches(tmp_path):
    retriever = build_retriever(tmp_path)
    retriever.add_documents(
        [
            Chunk(id="a", text="ldl cholesterol levels rising", metadata={"source": "a"}),
            Chunk(id="b", text="statin dosage changed last visit", metadata={"source": "b"}),
            Chunk(id="c", text="daily exercise routine unrelated to labs", metadata={"source": "c"}),
        ]
    )

    results = retriever.retrieve("ldl cholesterol statin", top_k=2)

    assert {c.id for c in results} == {"a", "b"}


def test_retrieve_returns_empty_when_no_documents(tmp_path):
    retriever = build_retriever(tmp_path)
    assert retriever.retrieve("anything") == []
