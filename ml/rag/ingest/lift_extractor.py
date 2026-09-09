"""
LiftExtractor: Visual document extraction using datalab-to/lift 9.7B VLM.

Supports:
- Single-pass visual extraction of multi-page PDFs and images.
- 4-bit NF4 quantization on CUDA via BitsAndBytesConfig (~6GB VRAM).
- Graceful CPU execution when CUDA is unavailable (without bitsandbytes).
- Fast deterministic mock mode when PHIRE_MOCK_LIFT=true.
"""

import os
from pathlib import Path
from typing import Any

from ml.rag.ingest.lift_schema import CLINICAL_DOCUMENT_SCHEMA, validate_lift_payload

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".webp"})
DEFAULT_MODEL_ID = os.environ.get("LIFT_MODEL", "datalab-to/lift")


class LiftExtractor:
    """Extracts structured clinical data from PDFs and images via datalab-to/lift."""

    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or DEFAULT_MODEL_ID
        self._model = None

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in SUPPORTED_EXTENSIONS

    def _get_model(self):
        """Lazy loader with device detection and quantization setup."""
        if self._model is not None:
            return self._model

        import torch

        # Import lift's InferenceManager
        try:
            from lift.model import InferenceManager
        except ImportError:
            raise ImportError(
                "lift-pdf package not installed. Install with: pip install 'lift-pdf[hf]'"
            )

        if torch.cuda.is_available():
            # In CUDA mode: 4-bit NF4 quantization via BitsAndBytesConfig
            try:
                from transformers import BitsAndBytesConfig

                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                )
                try:
                    self._model = InferenceManager(
                        method="hf",
                        model_name=self.model_id,
                        quantization_config=quantization_config,
                    )
                except TypeError:
                    self._model = InferenceManager(method="hf")
            except (ImportError, Exception):
                self._model = InferenceManager(method="hf")
        else:
            # In CPU mode: standard precision, device=cpu; strictly no BitsAndBytesConfig
            try:
                self._model = InferenceManager(
                    method="hf",
                    model_name=self.model_id,
                    device="cpu",
                    torch_dtype=torch.float32,
                )
            except TypeError:
                self._model = InferenceManager(method="hf")

        return self._model

    def extract(self, file_path: Path) -> dict[str, Any]:
        """Extract structured clinical JSON from a PDF or image file."""
        if not self.supports(file_path):
            raise ValueError(f"Unsupported file format {file_path.suffix} for Lift extraction.")

        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check for fast mock mode (used for testing and CPU development)
        if os.environ.get("PHIRE_MOCK_LIFT", "").lower() in ("1", "true", "yes"):
            return self._generate_mock_payload(file_path)

        model = self._get_model()

        # Lift's extract interface
        try:
            from lift import extract
            raw_output = extract(str(file_path), CLINICAL_DOCUMENT_SCHEMA, model=model)
            if hasattr(raw_output, "extraction"):
                raw_output = raw_output.extraction
        except Exception as exc:
            # Fallback or error logging
            raise RuntimeError(f"Lift extraction failed for {file_path}: {exc}") from exc
        finally:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        return validate_lift_payload(raw_output)

    def _generate_mock_payload(self, file_path: Path) -> dict[str, Any]:
        """Generate deterministic mock payload for fast unit test execution."""
        return {
            "document_date": "2026-03-10",
            "document_type": "Diagnostic Laboratory Report",
            "observations": [
                {
                    "name": "LDL Cholesterol",
                    "value": "162",
                    "unit": "mg/dL",
                    "reference_range": "0-100",
                    "interpretation": "High",
                },
                {
                    "name": "HDL Cholesterol",
                    "value": "48",
                    "unit": "mg/dL",
                    "reference_range": "> 40",
                    "interpretation": "Normal",
                },
                {
                    "name": "Fasting Blood Glucose",
                    "value": "104",
                    "unit": "mg/dL",
                    "reference_range": "70-99",
                    "interpretation": "High",
                },
            ],
            "medications": [
                {
                    "name": "Atorvastatin",
                    "dosage": "20 mg",
                    "frequency": "once daily at bedtime",
                    "status": "started",
                }
            ],
            "conditions": [
                {"name": "Hyperlipidemia", "status": "active"},
                {"name": "Impaired Fasting Glucose", "status": "active"},
            ],
            "narrative_sections": [
                {
                    "heading": "Impression",
                    "content": "Atherogenic dyslipidemia with borderline elevated fasting glycemia. Recommend lifestyle modification and statin therapy.",
                }
            ],
        }
