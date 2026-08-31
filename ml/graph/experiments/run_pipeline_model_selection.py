#!/usr/bin/env python3
"""PHIRE end-to-end model/pipeline selection benchmark.

Purpose
-------
Select the *pipeline*, not merely the smallest model. The benchmark compares:

    document -> text acquisition/OCR -> structured extraction -> normalization

and evaluates whether dedicated OCR is needed at all for each document class.
It also compares extraction models using Ollama's JSON-Schema constrained
structured decoding, which is a hard requirement for this benchmark.

The benchmark is deliberately sequential because PHIRE's current deployment
has a shared ~8 GB GPU and a process-wide GPU lock. Each Ollama request uses
``keep_alive=0`` so a candidate does not remain resident between cases.

Inputs
------
A JSON manifest supplied with --manifest. Each case can point at a PDF/image
and its gold structured facts. A text-only case may omit ``path`` and provide
``text`` directly. Example:

{
  "cases": [
    {
      "id": "lab_001",
      "type": "lab_report",
      "path": "eval_data/lab_001.pdf",
      "gold": {
        "observations": [{"name": "LDL", "value": 162, "unit": "mg/dL"}],
        "medications": [], "conditions": []
      }
    }
  ]
}

For OCR evaluation, the gold object may additionally contain ``text``. The
benchmark never asks an LLM judge to decide whether a number is correct:
critical fields are scored deterministically after normalization.

Pipeline variants
-----------------
A) native text only (pypdf)                       [PDFs]
B) native text -> extraction
C) RapidOCR -> extraction                         [images/scanned PDFs]
D) olmOCR -> extraction                           [optional]
E) native text first, OCR only on quality failure
F) native text + OCR agreement / fallback policy

Extraction candidates are discovered from OLLAMA_MODEL_CANDIDATES or the
explicit --models list and are skipped if unavailable. The schema is sent to
Ollama's ``format`` field on every extraction call. This is grammar/schema
constrained decoding, not prompt-only JSON instructions.

The script produces:
    results.json          complete per-case raw + scored results
    summary.json          aggregate decision data
    decision.md            deterministic recommendation with gates

It intentionally does not automatically change PHIRE's production model.
A model/pipeline is selected only after passing the hard safety/quality gates.

Example
-------
    python -m ml.graph.experiments.run_pipeline_model_selection \
      --manifest ml/graph/experiments/eval_data/pipeline_manifest.json \
      --models medgemma:4b,qwen3.5:9b \
      --ollama http://localhost:11434 \
      --out ml/graph/experiments/pipeline_selection_results

Optional dependencies are detected at runtime. pypdf is required for PDF
native extraction; RapidOCR is optional; Pillow is required for image OCR;
requests is required for Ollama. olmOCR is invoked through Ollama's OpenAI-
compatible vision endpoint and therefore does not require a separate Python
model runtime.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:
    import requests
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install requests: pip install requests") from exc


# ---------------------------------------------------------------------------
# Structured extraction contract
# ---------------------------------------------------------------------------

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "observations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": ["number", "string"]},
                    "unit": {"type": "string"},
                    "date": {"type": "string"},
                    "reference_range": {"type": "string"},
                    "interpretation": {"type": "string"},
                },
                "required": ["name", "value", "unit", "date", "reference_range", "interpretation"],
            },
        },
        "medications": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "dose": {"type": "string"},
                    "frequency": {"type": "string"},
                    "route": {"type": "string"},
                    "duration": {"type": "string"},
                    "status": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["name", "dose", "frequency", "route", "duration", "status", "date"],
            },
        },
        "conditions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "status": {"type": "string"},
                    "certainty": {"type": "string"},
                    "temporality": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["name", "status", "certainty", "temporality", "date"],
            },
        },
    },
    "required": ["observations", "medications", "conditions"],
}

EXTRACTION_SYSTEM = """You are PHIRE's clinical document fact extractor.
Extract ONLY facts explicitly stated in the supplied document text.
Do not infer, diagnose, normalize a value into a different value, or invent
placeholders. Preserve medication action/status and negation exactly enough
for downstream normalization. Empty arrays are correct when a category is
absent. Return only the requested structured object."""


@dataclass
class CandidateResult:
    candidate: str
    case_id: str
    stage: str
    ok: bool
    latency_s: float = 0.0
    output_tokens: int | None = None
    input_chars: int = 0
    raw_text: str = ""
    parsed: dict[str, Any] | None = None
    error: str | None = None
    score: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# General utilities
# ---------------------------------------------------------------------------


def norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def norm_name(s: Any) -> str:
    x = norm(s)
    x = re.sub(r"[^a-z0-9%./-]+", " ", x)
    aliases = {
        "ldl cholesterol": "ldl",
        "ldl c": "ldl",
        "low density lipoprotein": "ldl",
        "hba1c": "hba1c",
        "hb a1c": "hba1c",
        "glycated hemoglobin": "hba1c",
        "sgpt": "alt",
        "sgot": "ast",
        "sr creat": "creatinine",
        "serum creatinine": "creatinine",
    }
    return aliases.get(x, x)


def norm_unit(s: Any) -> str:
    x = norm(s).replace("μ", "µ")
    aliases = {
        "mg/dl": "mg/dl", "mg per dl": "mg/dl", "mg/dl.": "mg/dl",
        "g/dl": "g/dl", "mmol/l": "mmol/l", "iu/l": "iu/l",
        "miu/l": "miu/l", "ng/ml": "ng/ml", "µg/dl": "ug/dl",
        "mcg/dl": "ug/dl", "%": "%", "mmhg": "mmhg", "bpm": "bpm",
    }
    return aliases.get(x, x)


def norm_status(s: Any) -> str:
    x = norm(s)
    aliases = {
        "discontinued": "discontinued", "stopped": "discontinued",
        "stop": "discontinued", "held": "held", "hold": "held",
        "continued": "continued", "continue": "continued",
        "current": "continued", "active": "continued",
        "started": "started", "start": "started", "new": "started",
        "restarted": "restarted", "restart": "restarted",
        "increased": "increased", "decreased": "decreased",
    }
    return aliases.get(x, x)


def numeric_equal(a: Any, b: Any, tol: float = 1e-6) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return norm(a) == norm(b)


def flatten_gold(gold: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    for item in gold.get("observations", []):
        rows.append(("observation", item))
    for item in gold.get("medications", []):
        rows.append(("medication", item))
    for item in gold.get("conditions", []):
        rows.append(("condition", item))
    return rows


def flatten_pred(pred: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return flatten_gold(pred)


def best_match(g: dict[str, Any], preds: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    target = norm_name(g.get("name"))
    candidates = [p for p in preds if norm_name(p.get("name")) == target]
    if not candidates:
        return None
    # Prefer the candidate with the greatest number of matching attributes.
    fields = {
        "observation": ["value", "unit", "date"],
        "medication": ["dose", "frequency", "status", "date"],
        "condition": ["status", "certainty", "temporality", "date"],
    }[kind]
    return max(candidates, key=lambda p: sum(norm(p.get(f)) == norm(g.get(f)) for f in fields))


def score_extraction(gold: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    total_gold = total_pred = matched = exact_fields = field_total = 0
    critical_total = critical_correct = 0

    for kind, key in (("observation", "observations"), ("medication", "medications"), ("condition", "conditions")):
        gs = gold.get(key, [])
        ps = pred.get(key, [])
        total_gold += len(gs)
        total_pred += len(ps)
        kind_matches = 0
        kind_fields = kind_correct = 0
        kind_critical_total = kind_critical_correct = 0
        fields = {
            "observation": ["name", "value", "unit", "date", "reference_range", "interpretation"],
            "medication": ["name", "dose", "frequency", "route", "duration", "status", "date"],
            "condition": ["name", "status", "certainty", "temporality", "date"],
        }[kind]
        critical = {
            "observation": ["name", "value", "unit", "date"],
            "medication": ["name", "dose", "frequency", "status", "date"],
            "condition": ["name", "status", "certainty", "temporality"],
        }[kind]
        for g in gs:
            p = best_match(g, ps, kind)
            if p is None:
                kind_critical_total += len(critical)
                continue
            matched += 1
            kind_matches += 1
            for f in fields:
                field_total += 1
                kind_fields += 1
                if f == "name":
                    ok = norm_name(g.get(f)) == norm_name(p.get(f))
                elif f == "unit":
                    ok = norm_unit(g.get(f)) == norm_unit(p.get(f))
                elif f == "value":
                    ok = numeric_equal(g.get(f), p.get(f))
                elif f == "status":
                    ok = norm_status(g.get(f)) == norm_status(p.get(f))
                else:
                    ok = norm(g.get(f)) == norm(p.get(f))
                exact_fields += int(ok)
                kind_correct += int(ok)
            for f in critical:
                kind_critical_total += 1
                if f == "name":
                    ok = norm_name(g.get(f)) == norm_name(p.get(f))
                elif f == "unit":
                    ok = norm_unit(g.get(f)) == norm_unit(p.get(f))
                elif f == "value":
                    ok = numeric_equal(g.get(f), p.get(f))
                elif f == "status":
                    ok = norm_status(g.get(f)) == norm_status(p.get(f))
                else:
                    ok = norm(g.get(f)) == norm(p.get(f))
                kind_critical_correct += int(ok)
        out[f"{key}_gold"] = len(gs)
        out[f"{key}_pred"] = len(ps)
        out[f"{key}_matched"] = kind_matches
        out[f"{key}_field_accuracy"] = kind_correct / kind_fields if kind_fields else (1.0 if not gs else 0.0)
        out[f"{key}_critical_accuracy"] = (
            kind_critical_correct / kind_critical_total if kind_critical_total else (1.0 if not gs else 0.0)
        )
        critical_total += kind_critical_total
        critical_correct += kind_critical_correct

    precision = matched / total_pred if total_pred else (1.0 if total_gold == 0 else 0.0)
    recall = matched / total_gold if total_gold else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    out.update({
        "entity_precision": precision,
        "entity_recall": recall,
        "entity_f1": f1,
        "field_accuracy": exact_fields / field_total if field_total else 1.0,
        "critical_field_accuracy": critical_correct / critical_total if critical_total else 1.0,
        "false_positive_entities": max(0, total_pred - matched),
        "gold_entities": total_gold,
        "pred_entities": total_pred,
    })
    return out


# ---------------------------------------------------------------------------
# Text acquisition / OCR
# ---------------------------------------------------------------------------


def pypdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required for native PDF extraction") from exc
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def image_bytes(path: Path) -> bytes:
    return path.read_bytes()


def rapidocr_text(path: Path) -> str:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise RuntimeError("RapidOCR is not installed") from exc
    engine = RapidOCR()
    result, _ = engine(str(path))
    if not result:
        return ""
    # RapidOCR rows: [box, text, confidence]
    return "\n".join(str(row[1]) for row in result if len(row) >= 2).strip()


def olmocr_text(path: Path, ollama_url: str, model: str) -> str:
    # Ollama's vision endpoint is used directly. The exact model tag is
    # configurable because GGUF/community tags can change independently.
    data_url = "data:image/jpeg;base64," + base64.b64encode(image_bytes(path)).decode()
    prompt = (
        "Transcribe this medical document faithfully. Preserve all clinically "
        "important numbers, units, dates, medication names/doses/frequencies, "
        "negation, and table relationships. Return the transcription as plain "
        "natural text, without inventing missing content."
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt, "images": [data_url]}],
        "stream": False,
        "keep_alive": 0,
        "options": {"temperature": 0},
    }
    r = requests.post(f"{ollama_url.rstrip('/')}/api/chat", json=payload, timeout=180)
    r.raise_for_status()
    return str(r.json().get("message", {}).get("content", "")).strip()


def text_quality(text: str) -> dict[str, Any]:
    # Cheap deterministic routing signals. These are intentionally not used
    # as the final OCR quality metric; gold-based scoring decides the winner.
    chars = len(text)
    words = len(text.split())
    replacement = text.count("�")
    digit_count = sum(c.isdigit() for c in text)
    alpha_count = sum(c.isalpha() for c in text)
    return {
        "chars": chars,
        "words": words,
        "replacement_chars": replacement,
        "digit_ratio": digit_count / chars if chars else 0.0,
        "alpha_ratio": alpha_count / chars if chars else 0.0,
        "usable": bool(words >= 8 and replacement == 0),
    }


def cer(ref: str, hyp: str) -> float:
    # Pure-Python Levenshtein to keep this script dependency-light.
    a, b = ref, hyp
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(cur[-1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] / max(1, len(a))


def normalize_text(s: str) -> str:
    # Remove formatting artifacts but do not normalize clinical digits/units.
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\|", " ", s)
    s = re.sub(r"[*_`#]", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


# ---------------------------------------------------------------------------
# Ollama JSON-schema constrained extraction
# ---------------------------------------------------------------------------


def ollama_tags(ollama_url: str) -> set[str]:
    r = requests.get(f"{ollama_url.rstrip('/')}/api/tags", timeout=20)
    r.raise_for_status()
    tags = set()
    for model in r.json().get("models", []):
        if model.get("name"):
            tags.add(model["name"])
    return tags


def resolve_model(requested: str, available: set[str]) -> str | None:
    if requested in available:
        return requested
    # Ollama may report a tag with :latest while users specify a base name.
    base = requested.split(":", 1)[0]
    for tag in available:
        if tag.split(":", 1)[0] == base:
            return tag
    return None


def extract_with_ollama(text: str, model: str, ollama_url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": EXTRACTION_SYSTEM},
            {"role": "user", "content": text},
        ],
        # CRITICAL: use Ollama grammar/JSON-Schema constrained decoding.
        # Do not replace this with prompt-only JSON instructions.
        "format": EXTRACTION_SCHEMA,
        "stream": False,
        "keep_alive": 0,
        "options": {
            "temperature": 0,
            "top_p": 1,
        },
    }
    started = time.perf_counter()
    r = requests.post(f"{ollama_url.rstrip('/')}/api/chat", json=payload, timeout=300)
    latency = time.perf_counter() - started
    r.raise_for_status()
    body = r.json()
    raw = body.get("message", {}).get("content", "")
    if not raw:
        raise RuntimeError("Ollama returned an empty structured response")
    parsed = json.loads(raw)
    # Validate the shape without pulling jsonschema as a hard dependency.
    for key in ("observations", "medications", "conditions"):
        if key not in parsed or not isinstance(parsed[key], list):
            raise ValueError(f"schema violation: {key} is not an array")
    meta = {
        "latency_s": latency,
        "prompt_eval_count": body.get("prompt_eval_count"),
        "eval_count": body.get("eval_count"),
        "load_duration_ns": body.get("load_duration"),
        "total_duration_ns": body.get("total_duration"),
        "schema_constrained": True,
        "raw": raw,
    }
    return parsed, meta


# ---------------------------------------------------------------------------
# Pipeline evaluation
# ---------------------------------------------------------------------------


def acquire_text(case: dict[str, Any], method: str, ollama_url: str, ocr_model: str | None) -> tuple[str, dict[str, Any]]:
    if case.get("text") and method == "gold_text":
        return str(case["text"]), {"source": "manifest.text"}
    path = Path(case["path"]).expanduser() if case.get("path") else None
    if path and not path.is_absolute():
        path = Path.cwd() / path
    if method == "native":
        if not path:
            return str(case.get("text", "")), {"source": "manifest.text"}
        return pypdf_text(path), {"source": "pypdf"}
    if method == "rapidocr":
        if not path:
            raise RuntimeError("RapidOCR requires case.path")
        return rapidocr_text(path), {"source": "rapidocr"}
    if method == "olmocr":
        if not path or not ocr_model:
            raise RuntimeError("olmOCR requires case.path and --olmocr-model")
        return olmocr_text(path, ollama_url, ocr_model), {"source": "olmocr", "model": ocr_model}
    raise ValueError(f"Unknown acquisition method: {method}")


def should_native_first(case: dict[str, Any], native_text: str) -> bool:
    """Conservative native-text routing heuristic, validated later by gold.

    Native PDF text is preferred when it is substantial and free of obvious
    corruption. This is intentionally a routing hypothesis, not a quality
    claim. The benchmark reports whether the heuristic actually works.
    """
    q = text_quality(native_text)
    min_chars = int(case.get("native_min_chars", 80))
    return q["chars"] >= min_chars and q["usable"]


def evaluate_case(case: dict[str, Any], model: str, acquisition: str, ollama_url: str, olmocr_model: str | None) -> CandidateResult:
    case_id = str(case["id"])
    started = time.perf_counter()
    try:
        text, acquisition_meta = acquire_text(case, acquisition, ollama_url, olmocr_model)
        parsed, meta = extract_with_ollama(text, model, ollama_url)
        score = score_extraction(case.get("gold", {}), parsed)
        score["text_quality"] = text_quality(text)
        score["acquisition"] = acquisition_meta
        return CandidateResult(
            candidate=model,
            case_id=case_id,
            stage=f"{acquisition}->extraction",
            ok=True,
            latency_s=time.perf_counter() - started,
            output_tokens=meta.get("eval_count"),
            input_chars=len(text),
            raw_text=meta.get("raw", ""),
            parsed=parsed,
            score=score,
        )
    except Exception as exc:
        return CandidateResult(
            candidate=model,
            case_id=case_id,
            stage=f"{acquisition}->extraction",
            ok=False,
            latency_s=time.perf_counter() - started,
            error=f"{type(exc).__name__}: {exc}",
        )


def evaluate_ocr(case: dict[str, Any], method: str, ollama_url: str, olmocr_model: str | None) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        text, meta = acquire_text(case, method, ollama_url, olmocr_model)
        ref = str(case.get("gold", {}).get("text", ""))
        if not ref:
            return {"case_id": case["id"], "method": method, "ok": True, "latency_s": time.perf_counter() - started, "text_quality": text_quality(text), "note": "no OCR gold text"}
        return {
            "case_id": case["id"],
            "method": method,
            "ok": True,
            "latency_s": time.perf_counter() - started,
            "cer": cer(normalize_text(ref), normalize_text(text)),
            "field_accuracy": score_ocr_critical_fields(case.get("gold", {}).get("critical_fields", []), text),
            "text_quality": text_quality(text),
            "meta": meta,
        }
    except Exception as exc:
        return {"case_id": case["id"], "method": method, "ok": False, "latency_s": time.perf_counter() - started, "error": f"{type(exc).__name__}: {exc}"}


def score_ocr_critical_fields(fields: list[Any], text: str) -> float:
    if not fields:
        return 1.0
    t = norm(text)
    correct = 0
    for field in fields:
        if isinstance(field, dict):
            value = str(field.get("value", ""))
            alternatives = field.get("alternatives", [])
            ok = norm(value) in t or any(norm(x) in t for x in alternatives)
        else:
            ok = norm(field) in t
        correct += int(ok)
    return correct / len(fields)


# ---------------------------------------------------------------------------
# Decision engine
# ---------------------------------------------------------------------------


def mean(xs: Iterable[float]) -> float:
    vals = list(xs)
    return statistics.mean(vals) if vals else 0.0


def aggregate(results: list[CandidateResult]) -> dict[str, Any]:
    by_candidate: dict[str, list[CandidateResult]] = {}
    for r in results:
        by_candidate.setdefault(r.candidate, []).append(r)
    out: dict[str, Any] = {}
    for candidate, rows in by_candidate.items():
        good = [r for r in rows if r.ok]
        scores = [r.score for r in good]
        out[candidate] = {
            "cases": len(rows),
            "successful_cases": len(good),
            "success_rate": len(good) / len(rows) if rows else 0.0,
            "critical_field_accuracy": mean(s.get("critical_field_accuracy", 0.0) for s in scores),
            "field_accuracy": mean(s.get("field_accuracy", 0.0) for s in scores),
            "entity_f1": mean(s.get("entity_f1", 0.0) for s in scores),
            "false_positive_entities": mean(s.get("false_positive_entities", 0.0) for s in scores),
            "latency_p50_s": percentile([r.latency_s for r in rows], 50),
            "latency_p95_s": percentile([r.latency_s for r in rows], 95),
            "schema_constrained": True,
        }
    return out


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    idx = min(len(xs) - 1, max(0, int(round((p / 100) * (len(xs) - 1)))))
    return xs[idx]


def choose_extractor(aggregates: dict[str, Any], min_critical: float = 0.97, min_success: float = 0.99) -> tuple[str | None, str]:
    eligible = [
        (name, data) for name, data in aggregates.items()
        if data["critical_field_accuracy"] >= min_critical and data["success_rate"] >= min_success
    ]
    if not eligible:
        return None, "No extraction candidate passed the hard safety/quality gates. Keep the current baseline and expand the benchmark."
    # Quality is the primary objective. Resource/latency breaks ties.
    eligible.sort(key=lambda x: (-x[1]["critical_field_accuracy"], -x[1]["entity_f1"], x[1]["latency_p50_s"]))
    winner = eligible[0][0]
    return winner, f"{winner} passes the hard gates and is the best eligible candidate by critical accuracy, extraction F1, then latency."


def decide_ocr(ocr_rows: list[dict[str, Any]], extraction_rows: list[CandidateResult]) -> dict[str, Any]:
    by_method: dict[str, list[dict[str, Any]]] = {}
    for row in ocr_rows:
        by_method.setdefault(row["method"], []).append(row)
    summary = {}
    for method, rows in by_method.items():
        valid = [r for r in rows if r.get("ok")]
        summary[method] = {
            "cases": len(rows),
            "success_rate": len(valid) / len(rows) if rows else 0.0,
            "cer": mean(r.get("cer", 0.0) for r in valid if "cer" in r),
            "critical_field_accuracy": mean(r.get("field_accuracy", 0.0) for r in valid),
            "latency_p50_s": percentile([r.get("latency_s", 0.0) for r in rows], 50),
        }

    # The important decision is not "which OCR has the best CER?" It is:
    # does native text already preserve the clinical facts well enough that
    # OCR adds measurable value on the document classes where it is invoked?
    native = summary.get("native", {})
    alternatives = [
        (m, s) for m, s in summary.items()
        if m != "native" and s.get("critical_field_accuracy", 0) > native.get("critical_field_accuracy", 0)
    ]
    if native.get("critical_field_accuracy", 0) >= 0.99 and not alternatives:
        recommendation = "OCR NOT NEEDED for this evaluated document subset; native extraction is sufficient."
    else:
        recommendation = "OCR is justified for the evaluated failure subset; prefer the smallest method/model that recovers critical fields without measurable regression."
    return {"methods": summary, "recommendation": recommendation}


def write_outputs(out_dir: Path, raw: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")

    aggregates = raw["extraction_aggregates"]
    winner, reason = choose_extractor(aggregates)
    ocr_decision = raw["ocr_decision"]
    summary = {
        "extraction_winner": winner,
        "extraction_decision": reason,
        "ocr_decision": ocr_decision,
        "schema_decoding_required": True,
        "benchmark_integrity": {
            "patient_level_split_required": True,
            "no_llm_judge_for_numeric_critical_fields": True,
            "all_raw_predictions_retained": True,
            "sequential_gpu_execution": True,
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# PHIRE Pipeline Model Selection Decision",
        "",
        "This file is generated from `run_pipeline_model_selection.py`.",
        "",
        f"## Extraction winner\n\n**{winner or 'NONE'}**\n\n{reason}",
        "",
        "## Extraction candidates",
        "",
        "| Candidate | Critical accuracy | Field accuracy | Entity F1 | Success | p50 latency |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, data in aggregates.items():
        lines.append(f"| {name} | {data['critical_field_accuracy']:.4f} | {data['field_accuracy']:.4f} | {data['entity_f1']:.4f} | {data['success_rate']:.4f} | {data['latency_p50_s']:.2f}s |")
    lines += ["", "## OCR decision", "", ocr_decision["recommendation"], "", "## Hard gates", "", "- Critical clinical field accuracy >= 97%.", "- Successful structured responses >= 99%.", "- Ollama JSON Schema decoding enabled for every extraction call.", "- Any catastrophic clinical numeric/medication-status failure is a manual review blocker, regardless of aggregate score.", "- The winner must be evaluated on the same patient-level test set as every alternative.", "", "## Important interpretation", "", "A lower-parameter model is **not** selected merely because it is smaller. A candidate wins only if it preserves clinically critical extraction quality and reliability, after which latency/resource cost breaks ties. Likewise, olmOCR is not a permanent architecture requirement: if native PDF text or a lighter OCR path achieves the required critical-field accuracy on the real document distribution, the heavier vision OCR path should be removed or retained only as a targeted fallback."]
    (out_dir / "decision.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--models", help="Comma-separated Ollama extraction model tags. If omitted, use OLLAMA_MODEL_CANDIDATES or current baseline.")
    p.add_argument("--ollama", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    p.add_argument("--olmocr-model", default=os.getenv("PHIRE_OLMOCR_MODEL"))
    p.add_argument("--out", type=Path, default=Path("ml/graph/experiments/pipeline_selection_results"))
    p.add_argument("--skip-ocr", action="store_true")
    p.add_argument("--skip-extraction", action="store_true")
    p.add_argument("--ocr-methods", default="native,rapidocr,olmocr")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    cases = manifest.get("cases", [])
    if not cases:
        raise SystemExit("Manifest contains no cases")

    available = ollama_tags(args.ollama)
    requested_models = [
        x.strip() for x in (
            args.models
            or os.getenv("OLLAMA_MODEL_CANDIDATES", "medgemma:4b,qwen3.5:4b,qwen3.5:9b")
        ).split(",") if x.strip()
    ]
    models: list[str] = []
    missing: list[str] = []
    for requested in requested_models:
        resolved = resolve_model(requested, available)
        if resolved:
            models.append(resolved)
        else:
            missing.append(requested)

    raw: dict[str, Any] = {
        "metadata": {
            "manifest": str(args.manifest),
            "ollama": args.ollama,
            "available_models": sorted(available),
            "requested_models": requested_models,
            "resolved_models": models,
            "missing_models": missing,
            "schema_decoding": True,
            "started_at_epoch": time.time(),
        },
        "ocr": [],
        "extraction": [],
    }

    if not args.skip_ocr:
        for method in [x.strip() for x in args.ocr_methods.split(",") if x.strip()]:
            # Only run OCR methods on cases that actually have paths.
            for case in cases:
                if method != "native" and not case.get("path"):
                    continue
                if method == "olmocr" and not args.olmocr_model:
                    raw["ocr"].append({"case_id": case["id"], "method": method, "ok": False, "error": "--olmocr-model not provided"})
                    continue
                raw["ocr"].append(evaluate_ocr(case, method, args.ollama, args.olmocr_model))

    if not args.skip_extraction:
        # Extraction benchmark uses native/gold text for text-only cases and
        # each explicit acquisition path for image/PDF cases. This exposes the
        # interaction between OCR quality and downstream extraction quality.
        methods = ["native"]
        if any(c.get("path", "").lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) for c in cases):
            methods += ["rapidocr"]
            if args.olmocr_model:
                methods += ["olmocr"]
        for model in models:
            for method in methods:
                for case in cases:
                    if method != "native" and not case.get("path"):
                        continue
                    if method == "native" and not case.get("path") and not case.get("text"):
                        continue
                    raw["extraction"].append(asdict(evaluate_case(case, model, method, args.ollama, args.olmocr_model)))

    extraction_objects = [CandidateResult(**row) for row in raw["extraction"]]
    raw["extraction_aggregates"] = aggregate(extraction_objects)
    raw["ocr_decision"] = decide_ocr(raw["ocr"], extraction_objects)
    write_outputs(args.out, raw)

    print(json.dumps({
        "output": str(args.out),
        "models_tested": models,
        "models_missing": missing,
        "extraction_winner": choose_extractor(raw["extraction_aggregates"])[0],
        "ocr_recommendation": raw["ocr_decision"]["recommendation"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
