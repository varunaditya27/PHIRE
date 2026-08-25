"""
Runs RapidOCR against the existing 12-image OCR eval set (shared with
ml/rag/ingest/experiments — same documents, same ground truth) and scores
latency, confidence, and accuracy. See RESULTS.md for the write-up,
including why Surya OCR has no live run here.

    ml/.venv/bin/python -m ml.rag.ingest.router_experiments.run_benchmark
"""

import json
import time
from pathlib import Path

from ml.rag.ingest.experiments.eval_data import EVAL_ITEMS
from ml.rag.ingest.experiments.metrics import (
    character_error_rate,
    content_character_error_rate,
    content_word_error_rate,
    field_accuracy,
    word_error_rate,
)
from ml.rag.ingest.router_experiments.candidates import RapidOCRCandidate

OUTPUT_PATH = Path(__file__).resolve().parent / "results.json"


def evaluate(candidate) -> dict:
    """Run one candidate over every eval image and score latency + accuracy."""
    per_item = []
    totals = {"cer": [], "wer": [], "content_cer": [], "content_wer": [], "field_accuracy": [], "latency_seconds": [], "confidence": []}
    for item in EVAL_ITEMS:
        outcome = candidate.run(item["image_path"])
        text = outcome["text"]
        scores = {
            "cer": character_error_rate(text, item["ground_truth"]),
            "wer": word_error_rate(text, item["ground_truth"]),
            "content_cer": content_character_error_rate(text, item["ground_truth"]),
            "content_wer": content_word_error_rate(text, item["ground_truth"]),
            "field_accuracy": field_accuracy(text, item["key_fields"]),
            "latency_seconds": outcome["latency_seconds"],
            "confidence": outcome["confidence"],
        }
        for key, value in scores.items():
            totals[key].append(value)
        per_item.append({
            "id": item["id"], "variant": item["variant"],
            **{k: round(v, 4) for k, v in scores.items()},
            "text": text,
        })

    n = len(EVAL_ITEMS)
    return {
        "model": candidate.name,
        **{key: round(sum(values) / n, 4) for key, values in totals.items()},
        "per_item": per_item,
    }


def main() -> None:
    print(f"Eval set: {len(EVAL_ITEMS)} images\n")
    results = []
    for candidate in [RapidOCRCandidate()]:
        print(f"--- {candidate.name} ---")
        start = time.time()
        result = evaluate(candidate)
        results.append(result)
        print(f"  cer={result['cer']} content_cer={result['content_cer']} "
              f"field_accuracy={result['field_accuracy']} confidence={result['confidence']} "
              f"mean_latency={sum(i['latency_seconds'] for i in result['per_item']) / len(result['per_item']):.3f}s "
              f"(total {time.time() - start:.1f}s)")

    OUTPUT_PATH.write_text(json.dumps(results, indent=2))

    print(f"\n{'Model':<12} {'CER':>7} {'ContentCER':>11} {'WER':>7} {'ContentWER':>11} {'FieldAcc':>9} {'Confidence':>11} {'MeanLatency':>12}")
    for r in results:
        mean_latency = sum(i["latency_seconds"] for i in r["per_item"]) / len(r["per_item"])
        print(f"{r['model']:<12} {r['cer']:>7} {r['content_cer']:>11} {r['wer']:>7} "
              f"{r['content_wer']:>11} {r['field_accuracy']:>9} {r['confidence']:>11} {mean_latency:>11.3f}s")
    print(f"\nFull per-item output written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
