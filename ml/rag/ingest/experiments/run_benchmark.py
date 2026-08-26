"""
OCR-model-selection benchmark for the planned OCR extractor in
ml/rag/ingest/patient_documents.py.

Runs each candidate in candidates.py against every image in
eval_data/EVAL_ITEMS (6 documents x clean/photo variants) and scores raw
+ markup-normalized character/word error rate plus field-level accuracy.
Run from the repo root (requires the four model tags already pulled — see
RESULTS.md):

    ml/.venv/bin/python -m ml.rag.ingest.experiments.run_benchmark

Unlike the embedding/NLI benchmarks, candidates here are Ollama-hosted
models, not held in this process's own memory/VRAM — Ollama manages
loading/unloading between calls, so there's no manual GPU cleanup step.
Writes full per-item transcriptions to results.json (raw evidence for
audit) and prints an aggregate metrics table. See RESULTS.md for the
write-up and final decision.
"""

import json
import time
from pathlib import Path

from ml.rag.ingest.experiments.candidates import CANDIDATE_FACTORIES
from ml.rag.ingest.experiments.eval_data import EVAL_ITEMS
from ml.rag.ingest.experiments.metrics import (
    content_character_error_rate,
    content_word_error_rate,
    character_error_rate,
    field_accuracy,
    word_error_rate,
)

OUTPUT_PATH = Path(__file__).resolve().parent / "results.json"


def evaluate_candidate(candidate) -> dict:
    """Run one candidate over every eval image and score it against ground truth."""
    per_item = []
    totals = {"cer": [], "wer": [], "content_cer": [], "content_wer": [], "field_accuracy": []}
    for item in EVAL_ITEMS:
        transcription = candidate.extract(item["image_path"])
        scores = {
            "cer": character_error_rate(transcription, item["ground_truth"]),
            "wer": word_error_rate(transcription, item["ground_truth"]),
            "content_cer": content_character_error_rate(transcription, item["ground_truth"]),
            "content_wer": content_word_error_rate(transcription, item["ground_truth"]),
            "field_accuracy": field_accuracy(transcription, item["key_fields"]),
        }
        for key, value in scores.items():
            totals[key].append(value)
        per_item.append({
            "id": item["id"], "variant": item["variant"],
            **{k: round(v, 4) for k, v in scores.items()},
            "transcription": transcription,
        })

    n = len(EVAL_ITEMS)
    return {
        "model": candidate.name,
        **{key: round(sum(values) / n, 4) for key, values in totals.items()},
        "per_item": per_item,
    }


def main() -> None:
    print(f"Eval set: {len(EVAL_ITEMS)} images, {len(CANDIDATE_FACTORIES)} candidates\n")
    results = []
    for name, build in CANDIDATE_FACTORIES:
        print(f"--- {name} ---")
        start = time.time()
        candidate = build()
        result = evaluate_candidate(candidate)
        results.append(result)
        print(f"  cer={result['cer']} content_cer={result['content_cer']} "
              f"field_accuracy={result['field_accuracy']} ({time.time() - start:.1f}s)")

    OUTPUT_PATH.write_text(json.dumps(results, indent=2))

    print(f"\n{'Model':<40} {'CER':>7} {'ContentCER':>11} {'WER':>7} {'ContentWER':>11} {'Field Acc':>10}")
    for r in results:
        print(f"{r['model']:<40} {r['cer']:>7} {r['content_cer']:>11} {r['wer']:>7} "
              f"{r['content_wer']:>11} {r['field_accuracy']:>10}")
    print(f"\nFull per-item transcriptions written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
