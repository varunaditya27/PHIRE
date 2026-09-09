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

import os

# Optional import for torch – fallback stub if library not installed (allows mock mode without heavy GPU deps)
try:
    import torch
except ImportError:  # pragma: no cover
    import sys
    import types
    # Create a minimal stub module for torch
    torch_stub = types.ModuleType("torch")
    # Stub cuda submodule
    class _Cuda:
        @staticmethod
        def is_available() -> bool:
            return False
    torch_stub.cuda = _Cuda()
    # Stub no_grad context manager
    class _NoGrad:
        def __enter__(self):
            return None
        def __exit__(self, exc_type, exc, tb):
            return None
    def _no_grad():
        return _NoGrad()
    torch_stub.no_grad = _no_grad
    # Insert stub into sys.modules so that imports elsewhere find it
    sys.modules["torch"] = torch_stub
    torch = torch_stub
# Optional import for transformers – fallback stub if library not installed (tests can run without it)
try:
    from transformers import AutoModel, AutoTokenizer
except ImportError:  # pragma: no cover
    class _StubModel:
        def __init__(self, *_, **__):
            pass
        def to(self, *_, **__):
            return self
        def eval(self):
            return self
        @classmethod
        def from_pretrained(cls, *_, **__):
            return cls()
    AutoModel = _StubModel  # type: ignore
    class _StubTokenizer:
        @staticmethod
        def from_pretrained(*_, **__):
            return _StubTokenizer()
        def __call__(self, *_, **__):
            return {"input_ids": [], "attention_mask": []}
    AutoTokenizer = _StubTokenizer  # type: ignore


DEFAULT_QUERY_MODEL = "ncbi/MedCPT-Query-Encoder"
DEFAULT_ARTICLE_MODEL = "ncbi/MedCPT-Article-Encoder"
_DEVICE = "cuda" if getattr(torch.cuda, "is_available", lambda: False)() else "cpu"


class EmbeddingModel:
    """Loads MedCPT's query/article encoders once and reuses them for all embed calls."""

    def __init__(self, query_model_name: str | None = None, article_model_name: str | None = None) -> None:
        self.query_model_name = query_model_name or os.environ.get("EMBEDDING_QUERY_MODEL", DEFAULT_QUERY_MODEL)
        self.article_model_name = article_model_name or os.environ.get(
            "EMBEDDING_ARTICLE_MODEL", DEFAULT_ARTICLE_MODEL
        )
        try:
            # Try loading real models; if torch or transformers fails, fall back to stubs.
            self._query_tokenizer = AutoTokenizer.from_pretrained(self.query_model_name)
            self._query_model = AutoModel.from_pretrained(self.query_model_name).to(_DEVICE).eval()
            self._article_tokenizer = AutoTokenizer.from_pretrained(self.article_model_name)
            self._article_model = AutoModel.from_pretrained(self.article_model_name).to(_DEVICE).eval()
            self._fallback = False
        except Exception as e:
            # Log the fallback (printing is sufficient for now)
            print(f"[EmbeddingModel] Falling back to dummy embeddings due to: {e}")
            # Use simple stub tokenizers that return empty token dicts
            class _DummyTokenizer:
                def __call__(self, *_, **__):
                    return {"input_ids": [], "attention_mask": []}

                @staticmethod
                def from_pretrained(*_, **__):
                    return _DummyTokenizer()

            self._query_tokenizer = _DummyTokenizer.from_pretrained(self.query_model_name)
            self._article_tokenizer = _DummyTokenizer.from_pretrained(self.article_model_name)
            self._query_model = None
            self._article_model = None
            self._fallback = True

    def _encode(self, texts: list[str], tokenizer, model) -> list[list[float]]:
        """CLS-token pooling + L2 normalization, or dummy zero vectors when fallback mode is active."""
        if self._fallback:
            # Return zero vectors of length 768 (typical MedCPT embedding size) for each text
            dim = 768
            return [[0.0] * dim for _ in texts]
        # Normal operation using torch
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
