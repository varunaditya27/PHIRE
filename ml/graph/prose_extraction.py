"""
LLM-based extraction of medications, conditions, and observations from
free-text patient document sections (progress notes, radiology reports)
— the harder counterpart to table_parsing.py's deterministic table
extraction, since prose has no explicit schema to parse from.

Method/model choice benchmarked, not assumed: hand-rolled schema-
constrained Ollama extraction with qwen3.5:9b, chosen over Google
LangExtract after both were tested across three models — see
ml/graph/experiments/RESULTS.md. qwen3.5:9b matched a 27B alternative
exactly while running ~13x faster, and neither qwen3.5 size exhibited a
smaller model's hallucinated-placeholder or dropped-medication failures
observed in that benchmark.
"""

import json
import os

import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("PROSE_EXTRACTION_MODEL", "qwen3.5:9b")

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "medications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "dosage": {"type": "string"},
                    "frequency": {"type": "string"},
                    "status": {"type": "string", "enum": ["started", "continued", "discontinued", "unspecified"]},
                },
                "required": ["name"],
            },
        },
        "conditions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "status": {"type": "string", "enum": ["active", "resolved", "historical", "unspecified"]},
                },
                "required": ["name"],
            },
        },
        "observations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "value": {"type": "string"}},
                "required": ["name", "value"],
            },
        },
    },
    "required": ["medications", "conditions", "observations"],
}

EXTRACTION_PROMPT = (
    "Extract every medication mention, clinical condition/diagnosis, and clinical "
    "measurement/observation from the CLINICAL NOTE below.\n\n"
    'For each medication: name, dosage (if stated), frequency (if stated), and '
    'status ("started"/"continued"/"discontinued"/"unspecified").\n\n'
    'For each condition: name and status ("active"/"resolved"/"historical"/'
    '"unspecified" based on context).\n\n'
    "For each observation: name and value exactly as stated (including units).\n\n"
    "Only extract facts explicitly stated in the text -- do not infer or guess "
    "values that aren't written down.\n\n"
    "CLINICAL NOTE:\n{text}"
)


def extract_facts(text: str, model: str | None = None) -> dict:
    """Extract medications, conditions, and observations from free-text clinical content.

    Returns empty lists (not an exception) on *any* failure — network
    error, malformed response, or unparseable output — not just a JSON
    parse failure. One document's extraction going wrong shouldn't abort
    ingestion of everything else that document produces (vector chunks,
    table-derived Observations); catching only json.JSONDecodeError left
    an Ollama connection error or malformed response body free to crash
    the whole ingest run, contradicting that contract (found via review).
    """
    empty_facts = {"medications": [], "conditions": [], "observations": []}
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model or DEFAULT_MODEL,
                "prompt": EXTRACTION_PROMPT.format(text=text),
                "stream": False,
                "format": EXTRACTION_SCHEMA,
                "options": {"temperature": 0.0},
                # Same reasoning as ml/rag/ingest/ocr.py: release VRAM right
                # after this one-off call, and qwen3.5 is a reasoning model
                # that silently discards its answer into an unread "thinking"
                # field without this being turned off (found live in
                # ml/graph/experiments/RESULTS.md).
                "keep_alive": 0,
                "think": False,
            },
            timeout=300,
        )
        response.raise_for_status()
        parsed = json.loads(response.json()["response"])
    except (requests.RequestException, KeyError, json.JSONDecodeError) as exc:
        print(f"prose_extraction.extract_facts failed, skipping this document's prose facts: {exc}")
        return empty_facts
    if not isinstance(parsed, dict):
        return empty_facts
    return {
        "medications": parsed.get("medications", []),
        "conditions": parsed.get("conditions", []),
        "observations": parsed.get("observations", []),
    }
