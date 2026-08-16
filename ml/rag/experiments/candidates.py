"""
Embedding model candidates compared in the embedding-model-selection
experiment (see RESULTS.md for shortlist rationale). Each candidate
exposes embed_passages/embed_queries so run_benchmark.py can treat all
seven interchangeably despite different architectures (single symmetric
encoder, asymmetric-prefix encoder, or MedCPT's true dual encoder).

Candidates are exposed as (name, factory) pairs rather than pre-built
instances — run_benchmark.py builds, evaluates, and discards one at a time
so all seven never sit in the 8GB VRAM budget simultaneously (see
CLAUDE.md's Hardware section for the actual GPU spec this targets).
"""

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class SentenceTransformerCandidate:
    """Wraps a Sentence-Transformers model, with optional asymmetric prefixes."""

    def __init__(self, name: str, model_id: str, query_prefix: str = "", passage_prefix: str = "") -> None:
        self.name = name
        self._model = SentenceTransformer(model_id, device=DEVICE)
        self._query_prefix = query_prefix
        self._passage_prefix = passage_prefix

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        prefixed = [self._passage_prefix + t for t in texts]
        return self._model.encode(prefixed, show_progress_bar=False, normalize_embeddings=True)

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        prefixed = [self._query_prefix + t for t in texts]
        return self._model.encode(prefixed, show_progress_bar=False, normalize_embeddings=True)


class MedCPTCandidate:
    """Wraps MedCPT's true dual encoder: separate query/article models, CLS pooling.

    Not a Sentence-Transformers model — NCBI ships it as raw query/article
    transformer.AutoModel checkpoints with CLS-token pooling, per the
    MedCPT model card.
    """

    def __init__(self) -> None:
        from transformers import AutoModel, AutoTokenizer

        self.name = "MedCPT"
        self._query_tokenizer = AutoTokenizer.from_pretrained("ncbi/MedCPT-Query-Encoder")
        self._query_model = AutoModel.from_pretrained("ncbi/MedCPT-Query-Encoder").to(DEVICE).eval()
        self._article_tokenizer = AutoTokenizer.from_pretrained("ncbi/MedCPT-Article-Encoder")
        self._article_model = AutoModel.from_pretrained("ncbi/MedCPT-Article-Encoder").to(DEVICE).eval()

    def _encode(self, texts: list[str], tokenizer, model) -> np.ndarray:
        with torch.no_grad():
            inputs = tokenizer(texts, truncation=True, padding=True, return_tensors="pt", max_length=512).to(DEVICE)
            cls_embeddings = model(**inputs).last_hidden_state[:, 0, :]
            normed = cls_embeddings / cls_embeddings.norm(dim=1, keepdim=True)
            return normed.cpu().numpy()

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        return self._encode(texts, self._article_tokenizer, self._article_model)

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        return self._encode(texts, self._query_tokenizer, self._query_model)


# (name, factory) pairs — factories are only called (and models only
# loaded) one at a time by run_benchmark.py, then discarded.
CANDIDATE_FACTORIES = [
    ("PubMedBERT (medical, PubMed-abstract-tuned)", lambda: SentenceTransformerCandidate(
        "PubMedBERT (medical, PubMed-abstract-tuned)", "NeuML/pubmedbert-base-embeddings",
    )),
    ("BioLORD-2023 (medical, clinical-sentence-tuned)", lambda: SentenceTransformerCandidate(
        "BioLORD-2023 (medical, clinical-sentence-tuned)", "FremyCompany/BioLORD-2023",
    )),
    ("MedCPT (medical, retrieval-specific dual encoder)", lambda: MedCPTCandidate()),
    ("BGE-base-en-v1.5 (general, 109M)", lambda: SentenceTransformerCandidate(
        "BGE-base-en-v1.5 (general, 109M)", "BAAI/bge-base-en-v1.5",
        query_prefix="Represent this sentence for searching relevant passages: ",
    )),
    ("BGE-large-en-v1.5 (general, 335M)", lambda: SentenceTransformerCandidate(
        "BGE-large-en-v1.5 (general, 335M)", "BAAI/bge-large-en-v1.5",
        query_prefix="Represent this sentence for searching relevant passages: ",
    )),
    ("E5-large-v2 (general, 335M)", lambda: SentenceTransformerCandidate(
        "E5-large-v2 (general, 335M)", "intfloat/e5-large-v2",
        query_prefix="query: ", passage_prefix="passage: ",
    )),
    ("MXBai-embed-large-v1 (general, 335M)", lambda: SentenceTransformerCandidate(
        "MXBai-embed-large-v1 (general, 335M)", "mixedbread-ai/mxbai-embed-large-v1",
        query_prefix="Represent this sentence for searching relevant passages: ",
    )),
]
