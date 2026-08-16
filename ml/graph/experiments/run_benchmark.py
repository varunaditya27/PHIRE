"""
Prose-extraction method/model-selection benchmark. Run from the repo
root (requires the three model tags pulled -- see candidates.py):

    ml/.venv/bin/python -m ml.graph.experiments.run_benchmark

Runs each of 6 candidates (2 methods x 3 models) against all 3 documents
in eval_data.py, scores medication (name/dosage/frequency/status) and
observation (name/value) accuracy, writes full per-document extractions
to results.json, and prints an aggregate table. See RESULTS.md for the
write-up and final decision.
"""

import json
import time
from pathlib import Path

from ml.graph.experiments.candidates import CANDIDATE_FACTORIES
from ml.graph.experiments.eval_data import DOCUMENTS
from ml.graph.experiments.metrics import score_medications, score_observations

OUTPUT_PATH = Path(__file__).resolve().parent / "results.json"


def evaluate_candidate(candidate) -> dict:
    """Run one candidate over every eval document and score it against ground truth."""
    per_document = []
    totals = {"med_name_recall": [], "med_dosage": [], "med_frequency": [], "med_status": [],
              "obs_name_recall": [], "obs_value": []}
    for doc in DOCUMENTS:
        extracted = candidate.extract(doc["text"])
        med_scores = score_medications(extracted["medications"], doc["medications"])
        obs_scores = score_observations(extracted["observations"], doc["observations"])
        totals["med_name_recall"].append(med_scores["name_recall"])
        totals["med_dosage"].append(med_scores["dosage_accuracy"])
        totals["med_frequency"].append(med_scores["frequency_accuracy"])
        totals["med_status"].append(med_scores["status_accuracy"])
        totals["obs_name_recall"].append(obs_scores["name_recall"])
        totals["obs_value"].append(obs_scores["value_accuracy"])
        per_document.append({
            "id": doc["id"], "extracted": extracted,
            "medication_scores": med_scores, "observation_scores": obs_scores,
        })

    n = len(DOCUMENTS)
    return {
        "model": candidate.name,
        **{key: round(sum(values) / n, 4) for key, values in totals.items()},
        "per_document": per_document,
    }


def main() -> None:
    print(f"Eval set: {len(DOCUMENTS)} documents, {len(CANDIDATE_FACTORIES)} candidates\n")
    results = []
    for name, build in CANDIDATE_FACTORIES:
        print(f"--- {name} ---")
        start = time.time()
        try:
            candidate = build()
            result = evaluate_candidate(candidate)
        except Exception as exc:  # noqa: BLE001 - one bad candidate (timeout, OOM) shouldn't lose the rest
            print(f"  FAILED: {exc}")
            result = {"model": name, "error": str(exc)}
        results.append(result)
        # Write after every candidate, not just at the end -- a later
        # candidate crashing shouldn't lose already-collected results
        # (verified live: this happened on the first full run).
        OUTPUT_PATH.write_text(json.dumps(results, indent=2))
        if "error" not in result:
            print(f"  med_name_recall={result['med_name_recall']} med_dosage={result['med_dosage']} "
                  f"med_status={result['med_status']} obs_value={result['obs_value']} ({time.time() - start:.1f}s)")

    results = [r for r in results if "error" not in r]

    print(f"\n{'Model':<30} {'MedName':>8} {'MedDose':>8} {'MedFreq':>8} {'MedStat':>8} {'ObsName':>8} {'ObsVal':>8}")
    for r in results:
        print(f"{r['model']:<30} {r['med_name_recall']:>8} {r['med_dosage']:>8} {r['med_frequency']:>8} "
              f"{r['med_status']:>8} {r['obs_name_recall']:>8} {r['obs_value']:>8}")
    print(f"\nFull per-document extractions written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
