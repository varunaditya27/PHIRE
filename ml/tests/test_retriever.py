"""
Unit tests for ml/rag/retriever.py's BM25 + Chroma fusion logic.

Uses a fake embedding model (no network/model download) so these tests run
fast and don't depend on Hugging Face availability.
"""

from ml.rag.retriever import Chunk, HybridRetriever, _tokenize


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


def test_tokenize_lowercases_strips_punctuation_and_drops_stopwords():
    assert _tokenize("Should I worry about a Mole on my skin?") == ["worry", "mole", "skin"]


def test_retriever_reloads_existing_chunks_on_fresh_instance(tmp_path):
    persist_dir = tmp_path / "chroma"
    first = HybridRetriever(embedding_model=FakeEmbeddingModel(), persist_dir=persist_dir)
    first.add_documents([Chunk(id="a", text="ldl cholesterol levels rising", metadata={"source": "a"})])

    # A fresh instance (e.g. a new backend process) should see chunks
    # ingested by a prior instance, since Chroma persists them to disk —
    # only self._chunks/BM25 needed rehydrating on init.
    second = HybridRetriever(embedding_model=FakeEmbeddingModel(), persist_dir=persist_dir)

    assert [c.id for c in second.retrieve("ldl cholesterol", top_k=1)] == ["a"]


def test_add_documents_overwrites_existing_chunk_with_same_id(tmp_path):
    retriever = build_retriever(tmp_path)
    retriever.add_documents([Chunk(id="a", text="statin dosage changed last visit", metadata={"v": 1})])

    # Re-ingesting the same id with new content (e.g. re-processing an
    # updated patient document) must replace it, not silently keep the
    # stale version — Chroma's add() no-ops on a duplicate id, which is
    # why add_documents uses upsert() instead.
    retriever.add_documents([Chunk(id="a", text="ldl cholesterol levels rising", metadata={"v": 2})])

    assert retriever._chunks["a"].text == "ldl cholesterol levels rising"
    stored = retriever._collection.get(ids=["a"], include=["documents", "metadatas"])
    assert stored["documents"][0] == "ldl cholesterol levels rising"
    assert stored["metadatas"][0]["v"] == 2


def test_delete_by_document_id_removes_only_that_documents_chunks(tmp_path):
    retriever = build_retriever(tmp_path)
    retriever.add_documents(
        [
            Chunk(id="patient_doc_doc1_0", text="ldl cholesterol levels rising", metadata={"document_id": "doc1"}),
            Chunk(id="patient_doc_doc1_1", text="statin dosage changed", metadata={"document_id": "doc1"}),
            Chunk(id="patient_doc_doc2_0", text="daily exercise routine", metadata={"document_id": "doc2"}),
        ]
    )

    retriever.delete_by_document_id("doc1")

    assert set(retriever._chunks) == {"patient_doc_doc2_0"}
    remaining = retriever._collection.get(include=[])
    assert remaining["ids"] == ["patient_doc_doc2_0"]
    # BM25 index rebuilt without the deleted chunks, not just self._chunks
    assert "patient_doc_doc1_0" not in retriever._bm25_ids
    assert "patient_doc_doc1_1" not in retriever._bm25_ids


def test_delete_by_document_id_is_a_noop_for_unknown_document(tmp_path):
    retriever = build_retriever(tmp_path)
    retriever.add_documents([Chunk(id="a", text="ldl cholesterol levels rising", metadata={"document_id": "doc1"})])

    retriever.delete_by_document_id("never-ingested")

    assert set(retriever._chunks) == {"a"}
