"""
Embedding pipeline for document chunks and reference passages.

Wraps MedCPT's dual encoder so ingestion (backend) and retrieval
(ml/rag/retriever.py) share one embedding implementation, keeping vector
dimensions and preprocessing consistent across both call sites.

Model choice: MedCPT (ncbi/MedCPT-Query-Encoder + ncbi/MedCPT-Article-
Encoder) — picked after a 215-passage/129-query benchmark against 6 other
candidates (medical and general-purpose, base and large) found it led on
Recall@5, Recall@10, and tied-best on Recall@3. See
ml/rag/experiments/RESULTS.md for the full comparison, methodology, and
limitations (synthetic eval set — revisit once ArchEHR-QA lands).

Unlike a standard Sentence-Transformers model, MedCPT is a true dual
encoder: queries and passages are embedded by two different models, both
loaded here for that reason — embed_documents/embed_query route to the
correct one internally so callers don't need to know this.
"""

import os

import torch
from transformers import AutoModel, AutoTokenizer

DEFAULT_QUERY_MODEL = "ncbi/MedCPT-Query-Encoder"
DEFAULT_ARTICLE_MODEL = "ncbi/MedCPT-Article-Encoder"
_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class EmbeddingModel:
    """Loads MedCPT's query/article encoders once and reuses them for all embed calls."""

    def __init__(self, query_model_name: str | None = None, article_model_name: str | None = None) -> None:
        self.query_model_name = query_model_name or os.environ.get("EMBEDDING_QUERY_MODEL", DEFAULT_QUERY_MODEL)
        self.article_model_name = article_model_name or os.environ.get(
            "EMBEDDING_ARTICLE_MODEL", DEFAULT_ARTICLE_MODEL
        )
        self._query_tokenizer = AutoTokenizer.from_pretrained(self.query_model_name)
        self._query_model = AutoModel.from_pretrained(self.query_model_name).to(_DEVICE).eval()
        self._article_tokenizer = AutoTokenizer.from_pretrained(self.article_model_name)
        self._article_model = AutoModel.from_pretrained(self.article_model_name).to(_DEVICE).eval()

    def _encode(self, texts: list[str], tokenizer, model) -> list[list[float]]:
        """CLS-token pooling + L2 normalization, per the MedCPT model card."""
        with torch.no_grad():
            inputs = tokenizer(texts, truncation=True, padding=True, return_tensors="pt", max_length=512).to(_DEVICE)
            cls_embeddings = model(**inputs).last_hidden_state[:, 0, :]
            normed = cls_embeddings / cls_embeddings.norm(dim=1, keepdim=True)
            return normed.cpu().tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of document chunks for storage in Chroma, via the article encoder."""
        return self._encode(texts, self._article_tokenizer, self._article_model)

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string at retrieval time, via the query encoder."""
        return self._encode([text], self._query_tokenizer, self._query_model)[0]
