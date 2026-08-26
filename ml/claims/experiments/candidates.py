"""
NLI model candidates for the claim-verification model-selection experiment
(see RESULTS.md for shortlist rationale).

MedRAGChecker (the paper PHIRE's docs cite for claim-level verification) is
not a pip-installable library — docs/OPEN_SOURCE_TOOLS.md itself lists
"MedRAGChecker pseudocode -> Python" as a TODO. This benchmark instead
picks the actual NLI model that will drive verifier.py's entailment
scoring, applying the same medical-vs-general, base-vs-large comparison
methodology used for the embedding-model benchmark (ml/rag/experiments/).

Candidates are exposed as (name, factory) pairs, built/evaluated/discarded
one at a time by run_benchmark.py — same VRAM-budget reasoning as the
embedding benchmark (see CLAUDE.md's Hardware section).
"""

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
_CANONICAL_LABELS = ("entailment", "neutral", "contradiction")


class NLICandidate:
    """Wraps a 3-way (entailment/neutral/contradiction) sequence-classification model.

    Label order isn't standardized across NLI checkpoints (verified by
    inspecting each model's config.json before adding it here) — reading
    id2label from the model's own config at load time, rather than
    hardcoding an assumed order, is what makes this safe to extend with
    new candidates later.
    """

    def __init__(self, name: str, model_id: str) -> None:
        self.name = name
        self._tokenizer = AutoTokenizer.from_pretrained(model_id)
        self._model = AutoModelForSequenceClassification.from_pretrained(model_id).to(DEVICE).eval()
        self._index_to_canonical = {
            idx: label.lower() for idx, label in self._model.config.id2label.items()
        }
        unmapped = set(self._index_to_canonical.values()) - set(_CANONICAL_LABELS)
        if unmapped:
            raise ValueError(f"{model_id} has unrecognized NLI labels: {unmapped}")

    def predict(self, premise: str, hypothesis: str) -> dict[str, float]:
        """Return a probability distribution over entailment/neutral/contradiction."""
        with torch.no_grad():
            inputs = self._tokenizer(
                premise, hypothesis, truncation=True, return_tensors="pt", max_length=256
            ).to(DEVICE)
            probs = torch.softmax(self._model(**inputs).logits[0], dim=-1).cpu().tolist()
        result = {label: 0.0 for label in _CANONICAL_LABELS}
        for idx, prob in enumerate(probs):
            result[self._index_to_canonical[idx]] += prob
        return result


# Medical-specialized (MedNLI-finetuned) vs. general-purpose (standard
# MNLI) candidates, base and large sizes — mirrors ml/rag/experiments'
# medical-vs-general comparison.
CANDIDATE_FACTORIES = [
    ("PubMedBERT-MedNLI (medical, MedNLI-finetuned)", lambda: NLICandidate(
        "PubMedBERT-MedNLI (medical, MedNLI-finetuned)", "pritamdeka/PubMedBERT-MNLI-MedNLI",
    )),
    ("BioLinkBERT-MedNLI (medical, MedNLI-finetuned)", lambda: NLICandidate(
        "BioLinkBERT-MedNLI (medical, MedNLI-finetuned)", "cnut1648/biolinkbert-mednli",
    )),
    ("DeBERTa-v3-base-NLI (general, 184M)", lambda: NLICandidate(
        "DeBERTa-v3-base-NLI (general, 184M)", "cross-encoder/nli-deberta-v3-base",
    )),
    ("BART-large-MNLI (general, 407M)", lambda: NLICandidate(
        "BART-large-MNLI (general, 407M)", "facebook/bart-large-mnli",
    )),
    ("DeBERTa-large-MNLI (general, 400M)", lambda: NLICandidate(
        "DeBERTa-large-MNLI (general, 400M)", "microsoft/deberta-large-mnli",
    )),
    ("RoBERTa-large-MNLI (general, 355M)", lambda: NLICandidate(
        "RoBERTa-large-MNLI (general, 355M)", "FacebookAI/roberta-large-mnli",
    )),
]
