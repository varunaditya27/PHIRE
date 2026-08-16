"""
NLI-model-selection benchmark for ml/claims/verifier.py.

Scores each candidate in candidates.py against the 129 hand-labeled
premise/hypothesis pairs in eval_data.py. Run from the repo root:

    ml/.venv/bin/python -m ml.claims.experiments.run_benchmark

Candidates are built, evaluated, and discarded one at a time (see
candidates.py) to fit the 8GB GPU documented in CLAUDE.md. Writes full
per-pair predictions to results.json (raw evidence for scrutiny/
reproducibility) and prints an aggregate metrics table. See RESULTS.md for
the write-up and final decision.
"""

import gc
import json
import time
from pathlib import Path

import torch

from ml.claims.experiments.candidates import CANDIDATE_FACTORIES
from ml.claims.experiments.eval_data import EVAL_PAIRS
from ml.claims.experiments.metrics import accuracy, per_class_f1

OUTPUT_PATH = Path(__file__).resolve().parent / "results.json"


def evaluate_candidate(candidate) -> dict:
    """Run one candidate over every eval pair and score it against the gold labels."""
    predictions, per_pair = [], []
    for pair in EVAL_PAIRS:
        probs = candidate.predict(pair["premise"], pair["hypothesis"])
        predicted_label = max(probs, key=probs.get)
        predictions.append(predicted_label)
        per_pair.append({
            "topic": pair["topic"], "hypothesis": pair["hypothesis"], "gold": pair["label"],
            "predicted": predicted_label, "probs": {k: round(v, 4) for k, v in probs.items()},
        })

    gold = [pair["label"] for pair in EVAL_PAIRS]
    return {
        "model": candidate.name,
        "accuracy": round(accuracy(predictions, gold), 4),
        "per_class": per_class_f1(predictions, gold),
        "per_pair": per_pair,
    }


def main() -> None:
    print(f"Eval set: {len(EVAL_PAIRS)} pairs, {len(CANDIDATE_FACTORIES)} candidates\n")
    results = []
    for name, build in CANDIDATE_FACTORIES:
        print(f"--- {name} ---")
        start = time.time()
        candidate = build()
        result = evaluate_candidate(candidate)
        results.append(result)
        contradiction_f1 = result["per_class"]["contradiction"]["f1"]
        print(f"  accuracy={result['accuracy']} contradiction_f1={contradiction_f1} ({time.time() - start:.1f}s)")

        del candidate
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    OUTPUT_PATH.write_text(json.dumps(results, indent=2))

    print(f"\n{'Model':<45} {'Accuracy':>9} {'Entail F1':>10} {'Neutral F1':>11} {'Contra F1':>10}")
    for r in results:
        pc = r["per_class"]
        print(f"{r['model']:<45} {r['accuracy']:>9} {pc['entailment']['f1']:>10} "
              f"{pc['neutral']['f1']:>11} {pc['contradiction']['f1']:>10}")
    print(f"\nFull per-pair predictions written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
