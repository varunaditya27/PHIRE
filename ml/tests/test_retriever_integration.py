"""
Integration test for ml/rag/retriever.py using the real MedCPT EmbeddingModel.

test_retriever.py only exercises the fusion plumbing with a fake embedder;
this test catches regressions the fake can't (wrong pooling, dimension
mismatch, MedCPT query/article model mismatch). It downloads/loads the real
MedCPT models on first run, so it's slower than the rest of the suite.
"""

from ml.rag.embeddings import EmbeddingModel
from ml.rag.retriever import Chunk, HybridRetriever


def test_retrieve_finds_semantic_match_with_real_embedding_model(tmp_path):
    retriever = HybridRetriever(embedding_model=EmbeddingModel(), persist_dir=tmp_path / "chroma")
    retriever.add_documents(
        [
            Chunk(
                id="ldl",
                text="LDL cholesterol was elevated at the last lab draw, statin dosage increased.",
                metadata={},
            ),
            Chunk(
                id="unrelated",
                text="Patient reports improved sleep quality after adjusting evening routine.",
                metadata={},
            ),
        ]
    )

    # Paraphrase, not a lexical match — only a real semantic embedder ranks
    # this correctly; the fake bag-of-words embedder in test_retriever.py
    # can't verify this.
    results = retriever.retrieve("has the patient's bad cholesterol been high recently?", top_k=1)

    assert [c.id for c in results] == ["ldl"]
