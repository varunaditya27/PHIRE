"""
Prose-extraction method/model candidates: hand-rolled schema-constrained
Ollama extraction (mirrors ml/rag/ingest/ocr.py's proven pattern) vs
Google LangExtract's native Ollama integration (source-grounded, but
loose JSON mode only -- see RESULTS.md for why a third option,
LangExtract wired to real schema constraints, was investigated and ruled
out as unsafe to depend on).

Each candidate returns {"medications": [...], "observations": [...]} in
the same shape regardless of method, so run_benchmark.py can score them
identically.
"""

import json
import os

import langextract as lx
import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

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
        "observations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "value": {"type": "string"}},
                "required": ["name", "value"],
            },
        },
    },
    "required": ["medications", "observations"],
}

EXTRACTION_PROMPT = (
    "Extract every medication mention and every clinical measurement/observation "
    "from the CLINICAL NOTE below.\n\n"
    'For each medication, capture its name, dosage (if stated), frequency (if '
    'stated), and status: "started" (newly prescribed), "continued" (already '
    'being taken, unchanged), "discontinued" (stopped), or "unspecified" if the '
    "status isn't clear from context.\n\n"
    "For each observation, capture its name and its value exactly as stated "
    "(including units).\n\n"
    "Only extract facts explicitly stated in the text -- do not infer or guess "
    "values that aren't written down.\n\n"
    "CLINICAL NOTE:\n{text}"
)


class HandRolledExtractor:
    """Direct schema-constrained Ollama call -- same proven pattern as ml/rag/ingest/ocr.py."""

    def __init__(self, name: str, model_tag: str) -> None:
        self.name = name
        self.model_tag = model_tag

    def extract(self, text: str) -> dict:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": self.model_tag,
                "prompt": EXTRACTION_PROMPT.format(text=text),
                "stream": False,
                "format": EXTRACTION_SCHEMA,
                "options": {"temperature": 0.0},
                "keep_alive": 0,
                # Reasoning models (e.g. qwen3.5) otherwise put the whole
                # answer in a separate "thinking" field and leave
                # "response" empty -- verified live: qwen3.5:9b's
                # extraction was actually perfect, just parsed as empty
                # because we weren't reading the right field.
                "think": False,
            },
            timeout=300,
        )
        response.raise_for_status()
        try:
            parsed = json.loads(response.json()["response"])
        except json.JSONDecodeError:
            return {"medications": [], "observations": []}
        return {"medications": parsed.get("medications", []), "observations": parsed.get("observations", [])}


# Two-shot: one example exercising all three medication statuses, one
# exercising a bare observation -- matches the eval set's actual shapes.
LANGEXTRACT_EXAMPLES = [
    lx.data.ExampleData(
        text=(
            "Continue home medications: Metformin 500mg twice daily. New: started "
            "warfarin 5mg daily for atrial fibrillation. Discontinued aspirin 81mg daily."
        ),
        extractions=[
            lx.data.Extraction(extraction_class="medication", extraction_text="Metformin",
                                attributes={"dosage": "500mg", "frequency": "twice daily", "status": "continued"}),
            lx.data.Extraction(extraction_class="medication", extraction_text="warfarin",
                                attributes={"dosage": "5mg", "frequency": "daily", "status": "started"}),
            lx.data.Extraction(extraction_class="medication", extraction_text="aspirin",
                                attributes={"dosage": "81mg", "frequency": "daily", "status": "discontinued"}),
        ],
    ),
    lx.data.ExampleData(
        text="Cardiothoracic ratio measured at 0.48, within normal limits.",
        extractions=[
            lx.data.Extraction(extraction_class="observation", extraction_text="Cardiothoracic ratio",
                                attributes={"value": "0.48"}),
        ],
    ),
]


class LangExtractCandidate:
    """Google LangExtract's native Ollama integration (loose JSON mode, source-grounded)."""

    def __init__(self, name: str, model_tag: str) -> None:
        self.name = name
        self.model_tag = model_tag

    def extract(self, text: str) -> dict:
        # Explicit provider, not model_id pattern auto-detection: LangExtract's
        # router only matches "^gemma", not "medgemma" -- found live when
        # medgemma:4b raised InferenceConfigError despite being Gemma-based.
        config = lx.factory.ModelConfig(
            model_id=self.model_tag, provider="OllamaLanguageModel",
            # Ollama provider defaults to a 120s request timeout -- too
            # short for a 17GB CPU-offloaded model (verified live: the
            # 27b candidate timed out at the default).
            provider_kwargs={"model_url": OLLAMA_HOST, "timeout": 600},
        )
        result = lx.extract(
            text_or_documents=text,
            prompt_description=(
                "Extract medication mentions (with dosage, frequency, and status: "
                "started/continued/discontinued/unspecified) and clinical observations "
                "(with value) from clinical text."
            ),
            examples=LANGEXTRACT_EXAMPLES,
            config=config,
            show_progress=False,
        )
        medications, observations = [], []
        for extraction in result.extractions:
            attrs = extraction.attributes or {}
            if extraction.extraction_class == "medication":
                medications.append({
                    "name": extraction.extraction_text, "dosage": attrs.get("dosage", ""),
                    "frequency": attrs.get("frequency", ""), "status": attrs.get("status", "unspecified"),
                })
            elif extraction.extraction_class == "observation":
                observations.append({"name": extraction.extraction_text, "value": attrs.get("value", "")})
        return {"medications": medications, "observations": observations}


# (name, factory) pairs -- method x model, built lazily.
_MODELS = [
    ("medgemma:4b", "medgemma:4b"),
    ("qwen3.5:9b", "qwen3.5:9b"),
    ("qwen3.5:27b-q4_K_M", "qwen3.5:27b-q4_K_M"),
]

CANDIDATE_FACTORIES = [
    (f"HandRolled + {model_name}", lambda tag=model_tag, name=model_name: HandRolledExtractor(f"HandRolled + {name}", tag))
    for model_name, model_tag in _MODELS
] + [
    (f"LangExtract + {model_name}", lambda tag=model_tag, name=model_name: LangExtractCandidate(f"LangExtract + {name}", tag))
    for model_name, model_tag in _MODELS
]
