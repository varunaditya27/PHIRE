"""
Claim verification against retrieved evidence.

Model choice: facebook/bart-large-mnli — picked after a 129-pair benchmark
against 5 other candidates (2 medical MedNLI-finetuned, 4 general MNLI)
found it led on accuracy and all three per-class F1 scores, including
beating both medical-specialized models. See
ml/claims/experiments/RESULTS.md for the full comparison, spot-check of
*why* the general model won, and limitations.

v1 status taxonomy this module itself produces: SUPPORTED, CONFLICTING,
UNCERTAIN, UNSUPPORTED — a single NLI entailment score can't reliably
distinguish "directly restates the evidence" from "requires reasoning
beyond it," so this module doesn't try to.

DERIVED (claim requires computing something from raw values, e.g. "LDL
increased 29 points" from two separate Observations) IS implemented, but
one layer up: ml/graph/patient_context.py's get_trend_facts() precomputes
the arithmetic as its own checkable sentence, and
ml/chains/qa_chain.py's QAChain._verify_claim relabels a SUPPORTED verdict
against that sentence as DERIVED. This module never sees a DERIVED
status — it only ever returns the four above.

INFERRED (claim requires multi-hop reasoning beyond direct restatement or
simple arithmetic) is NOT implemented anywhere yet — no validated signal
exists for it, and approximating that distinction without one would be
worse than being explicit about the gap. Collapses into SUPPORTED if the
matched evidence happens to entail the claim, or UNCERTAIN otherwise.
"""

import os
from dataclasses import dataclass

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from ml.rag.retriever import Chunk

DEFAULT_MODEL = "facebook/bart-large-mnli"
_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Calibrated against this model's own probability distribution on
# ml/claims/experiments/'s benchmark, not a generic cutoff — see
# RESULTS.md's per-class F1 at these implied thresholds.
# A batch is padded to its longest pair, so its cost is (pairs x longest length).
# Capping that product (and the pair count) keeps activation memory small next to
# the other resident models on an 8GB card, and -- combined with sorting by length --
# stops short patient-fact sentences being padded up to a 512-token passage.
BATCH_TOKEN_BUDGET = 2048
MAX_BATCH_PAIRS = 32

ENTAILMENT_THRESHOLD = 0.7
CONTRADICTION_THRESHOLD = 0.5


@dataclass
class ClaimVerification:
    """Verdict for one claim: its status, the NLI probabilities behind it, and the evidence used."""

    claim: str
    status: str
    entailment_prob: float
    contradiction_prob: float
    evidence: Chunk | None


class ClaimVerifier:
    """Checks each claim against retrieved evidence via NLI entailment/contradiction scoring."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.environ.get("NLI_MODEL", DEFAULT_MODEL)
        self._device = _DEVICE
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name).to(self._device).eval()
        self._index_to_label = {idx: label.lower() for idx, label in self._model.config.id2label.items()}

    def verify(self, claim: str, evidence: list[Chunk]) -> ClaimVerification:
        """Verify claim against the strongest-matching evidence chunk (or UNSUPPORTED if none provided)."""
        if not evidence:
            return ClaimVerification(claim, "UNSUPPORTED", 0.0, 0.0, None)

        scored = list(zip(evidence, self._predict_batch([chunk.text for chunk in evidence], claim)))
        # A chunk that clearly entails the claim wins over a contradiction
        # from any other chunk: NLI reports near-certain "contradiction"
        # between same-template sentences about *different* facts (e.g. an
        # HDL value vs an LDL claim), and picking by raw signal strength let
        # that unrelated chunk outrank the true match (seen live: a correct
        # patient LDL claim came back CONFLICTING). Otherwise the chunk with
        # the strongest signal in *either* direction is the most informative
        # one -- a chunk scored mostly "neutral" says nothing about the claim.
        entailing = [(c, p) for c, p in scored if p["entailment"] >= ENTAILMENT_THRESHOLD]
        if entailing:
            best_chunk, best_probs = max(entailing, key=lambda cp: cp[1]["entailment"])
        else:
            best_chunk, best_probs = max(scored, key=lambda cp: max(cp[1]["entailment"], cp[1]["contradiction"]))

        status = self._status_from_probs(best_probs)
        return ClaimVerification(claim, status, best_probs["entailment"], best_probs["contradiction"], best_chunk)

    def move_to(self, device: str) -> None:
        """Move weights to `device` -- lets the backend park this model in CPU RAM while lift owns the GPU."""
        self._device = device
        self._model.to(device)

    def _predict_batch(self, premises: list[str], hypothesis: str) -> list[dict[str, float]]:
        """NLI probability distribution for each (premise, hypothesis) pair, in input order.

        Batched instead of one forward pass per premise: a chat turn verifies every
        claim against up to ~100 evidence chunks, so the old per-chunk loop made
        ~100 tiny GPU calls per claim. Pairs are tokenized once, sorted by length,
        and packed into batches under BATCH_TOKEN_BUDGET so padding stays small.
        """
        encoded = self._tokenizer(
            premises, [hypothesis] * len(premises), truncation=True, max_length=512,
        )
        order = sorted(range(len(premises)), key=lambda i: len(encoded["input_ids"][i]))
        results: list[dict[str, float] | None] = [None] * len(premises)
        with torch.no_grad():
            for indices in self._pack_batches(order, [len(ids) for ids in encoded["input_ids"]]):
                batch = self._tokenizer.pad(
                    {key: [encoded[key][i] for i in indices] for key in ("input_ids", "attention_mask")},
                    return_tensors="pt",
                ).to(self._device)
                probs = torch.softmax(self._model(**batch).logits, dim=-1).cpu().tolist()
                for i, row in zip(indices, probs):
                    results[i] = {self._index_to_label[idx]: prob for idx, prob in enumerate(row)}
        return results  # type: ignore[return-value]  # every slot is filled above

    @staticmethod
    def _pack_batches(order: list[int], lengths: list[int]) -> list[list[int]]:
        """Group indices (already sorted by length ascending) so pairs x longest stays within budget."""
        batches: list[list[int]] = []
        current: list[int] = []
        for i in order:
            # lengths ascend, so the candidate pair is the batch's longest.
            if current and (len(current) + 1) * lengths[i] > BATCH_TOKEN_BUDGET or len(current) >= MAX_BATCH_PAIRS:
                batches.append(current)
                current = []
            current.append(i)
        if current:
            batches.append(current)
        return batches

    @staticmethod
    def _status_from_probs(probs: dict[str, float]) -> str:
        """Threshold entailment/contradiction into a v1 status (see module docstring for scope)."""
        if probs["contradiction"] >= CONTRADICTION_THRESHOLD:
            return "CONFLICTING"
        if probs["entailment"] >= ENTAILMENT_THRESHOLD:
            return "SUPPORTED"
        return "UNCERTAIN"
