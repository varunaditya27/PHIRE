"""
Unit tests for ml/claims/verifier.py's evidence-selection and status-
thresholding logic. Uses a stub subclass that skips loading the real NLI
model (no network/GPU dependency) and injects fixed predictions.
"""

from ml.claims.verifier import ClaimVerifier
from ml.rag.retriever import Chunk


class StubVerifier(ClaimVerifier):
    """ClaimVerifier with fixed per-chunk-id predictions, no model loaded."""

    def __init__(self, predictions: dict[str, dict[str, float]]) -> None:
        self._predictions = predictions

    def _predict_batch(self, premises: list[str], hypothesis: str) -> list[dict[str, float]]:
        return [self._predictions[premise] for premise in premises]


def test_verify_returns_unsupported_when_no_evidence():
    verifier = StubVerifier({})
    result = verifier.verify("claim", [])
    assert result.status == "UNSUPPORTED"
    assert result.evidence is None


def test_verify_returns_supported_above_entailment_threshold():
    chunk = Chunk(id="a", text="evidence text", metadata={})
    verifier = StubVerifier({"evidence text": {"entailment": 0.9, "neutral": 0.08, "contradiction": 0.02}})

    result = verifier.verify("claim", [chunk])

    assert result.status == "SUPPORTED"
    assert result.evidence.id == "a"


def test_verify_returns_conflicting_above_contradiction_threshold():
    chunk = Chunk(id="a", text="evidence text", metadata={})
    verifier = StubVerifier({"evidence text": {"entailment": 0.05, "neutral": 0.15, "contradiction": 0.8}})

    result = verifier.verify("claim", [chunk])

    assert result.status == "CONFLICTING"


def test_verify_returns_uncertain_below_both_thresholds():
    chunk = Chunk(id="a", text="evidence text", metadata={})
    verifier = StubVerifier({"evidence text": {"entailment": 0.4, "neutral": 0.5, "contradiction": 0.1}})

    result = verifier.verify("claim", [chunk])

    assert result.status == "UNCERTAIN"


def test_verify_picks_most_informative_chunk_over_a_neutral_one():
    neutral_chunk = Chunk(id="neutral", text="neutral text", metadata={})
    entailing_chunk = Chunk(id="entails", text="entailing text", metadata={})
    verifier = StubVerifier({
        "neutral text": {"entailment": 0.1, "neutral": 0.85, "contradiction": 0.05},
        "entailing text": {"entailment": 0.92, "neutral": 0.05, "contradiction": 0.03},
    })

    result = verifier.verify("claim", [neutral_chunk, entailing_chunk])

    assert result.evidence.id == "entails"
    assert result.status == "SUPPORTED"


def test_verify_entailing_chunk_beats_contradiction_from_unrelated_chunk():
    # Regression: same-template sentences about a different metric (HDL vs an
    # LDL claim) score ~1.0 "contradiction" under NLI and used to outrank the
    # true 0.99-entailing match, flipping a correct claim to CONFLICTING.
    evidence = [Chunk(id="unrelated", text="unrelated text", metadata={}), Chunk(id="match", text="matching text", metadata={})]
    verifier = StubVerifier({
        "unrelated text": {"entailment": 0.0, "neutral": 0.0, "contradiction": 1.0},
        "matching text": {"entailment": 0.99, "neutral": 0.01, "contradiction": 0.0},
    })
    result = verifier.verify("claim", evidence)
    assert result.status == "SUPPORTED"
    assert result.evidence.id == "match"


def test_pack_batches_respects_token_budget_and_pair_cap_and_covers_every_index():
    from ml.claims import verifier as v

    lengths = [10] * 5 + [100] * 4 + [512] * 6  # already ascending, as _predict_batch sorts
    batches = ClaimVerifier._pack_batches(list(range(len(lengths))), lengths)

    assert sorted(i for b in batches for i in b) == list(range(len(lengths)))  # nothing lost or duplicated
    for b in batches:
        assert len(b) <= v.MAX_BATCH_PAIRS
        # longest pair is last (ascending input); pairs x longest stays in budget unless a single pair exceeds it
        assert len(b) == 1 or len(b) * lengths[b[-1]] <= v.BATCH_TOKEN_BUDGET
    # the shortest pairs are never padded up to a 512-token pair (the case that made naive batching slower)
    assert all(max(lengths[i] for i in b) < 512 for b in batches if 0 in b)


def test_predict_batch_returns_results_in_input_order_despite_length_sorting():
    import torch

    class FakeTokenizer:
        def __call__(self, premises, hypotheses, truncation, max_length):
            ids = [[len(p)] * len(p) for p in premises]  # row i has len(premise i) tokens, all equal to that length
            return {"input_ids": ids, "attention_mask": [[1] * len(row) for row in ids]}

        def pad(self, features, return_tensors):
            width = max(len(row) for row in features["input_ids"])
            ids = torch.tensor([row + [0] * (width - len(row)) for row in features["input_ids"]])

            class Batch(dict):
                def to(self, device):
                    return self

            return Batch(input_ids=ids)

    class FakeModel:
        def __call__(self, input_ids):
            # logit 0 = the row's token value (its premise length), so each premise gets a distinct, checkable result
            logits = torch.zeros(input_ids.shape[0], 3)
            logits[:, 0] = input_ids[:, 0].float()
            return type("Out", (), {"logits": logits})()

    verifier = ClaimVerifier.__new__(ClaimVerifier)
    verifier._tokenizer, verifier._model, verifier._device = FakeTokenizer(), FakeModel(), "cpu"
    verifier._index_to_label = {0: "entailment", 1: "neutral", 2: "contradiction"}
    premises = ["a" * 30, "b" * 3, "c" * 12, "d" * 7]  # deliberately not sorted by length

    results = verifier._predict_batch(premises, "claim")

    expected = [torch.softmax(torch.tensor([float(len(p)), 0.0, 0.0]), dim=-1)[0].item() for p in premises]
    assert [round(r["entailment"], 6) for r in results] == [round(e, 6) for e in expected]


def test_place_uses_fp32_on_cpu_and_fp16_on_cuda():
    import pytest
    import torch

    verifier = ClaimVerifier.__new__(ClaimVerifier)
    verifier._model = torch.nn.Linear(2, 2)

    verifier.move_to("cpu")
    assert verifier._model.weight.dtype == torch.float32 and verifier._device == "cpu"

    if torch.cuda.is_available():
        verifier.move_to("cuda")
        assert verifier._model.weight.dtype == torch.float16
        verifier.move_to("cpu")  # parked on CPU while lift owns the GPU -> back to fp32
        assert verifier._model.weight.dtype == torch.float32 and not verifier._model.weight.is_cuda
    else:
        pytest.skip("no CUDA device to check the fp16 branch")
