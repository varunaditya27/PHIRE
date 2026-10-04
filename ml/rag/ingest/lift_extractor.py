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

    # Which GPU residency group (backend gpu_modes.py) this extractor needs while it runs.
    gpu_mode = "lift"

    def __init__(
        self,
        model_id: str | None = None,
        device: str | None = None,
        mock: bool | None = None,
    ) -> None:
        self.model_id = model_id or DEFAULT_MODEL_ID
        self.device = (device or os.environ.get("LIFT_DEVICE", "auto")).lower()
        self._mock = mock
        self._model = None

    @property
    def mock(self) -> bool:
        """Explicit constructor value wins; otherwise PHIRE_MOCK_LIFT, read at call time.

        Read lazily because patient_documents.py builds a module-level default
        extractor at import, before a caller or test has set the env var.
        """
        if self._mock is not None:
            return self._mock
        return os.environ.get("PHIRE_MOCK_LIFT", "").lower() in ("1", "true", "yes")

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in SUPPORTED_EXTENSIONS

    def _get_model(self):
        """Load lift once; on CUDA, quantize to 4-bit NF4 so the 9.7B model fits 8GB VRAM.

        lift's InferenceManager only accepts `method` -- it ignores or rejects
        any quantization/device kwargs and always loads bf16 (~18GB). So the
        quantized model is built here with transformers and injected into an
        InferenceManager. No silent fallback: if the 4-bit load fails, raise
        rather than quietly loading bf16 and spilling the model into CPU RAM.
        """
        if self._model is not None:
            return self._model

        import torch

        try:
            from lift.model import InferenceManager
            from lift.settings import settings as lift_settings
        except ImportError as exc:
            raise ImportError(
                "lift-pdf package not installed. Install with: pip install 'lift-pdf[hf]'"
            ) from exc

        lift_settings.MODEL_CHECKPOINT = self.model_id
        use_cuda = self.device in ("auto", "cuda") and torch.cuda.is_available()

        if not use_cuda:
            lift_settings.TORCH_DEVICE = "cpu"
            self._model = InferenceManager(method="hf")
            return self._model

        from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

        # Vision tower (0.46B) stays bf16: quantizing it hurts OCR fidelity for
        # little VRAM gain. The language model and lm_head are quantized.
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            llm_int8_skip_modules=["visual"],
        )
        model = AutoModelForImageTextToText.from_pretrained(
            self.model_id,
            quantization_config=quantization_config,
            dtype=torch.bfloat16,
            device_map={"": 0},
        ).eval()
        processor = AutoProcessor.from_pretrained(self.model_id)
        processor.tokenizer.padding_side = "left"
        model.processor = processor

        # "vllm" skips lift's own load_model(); we then swap in the quantized one.
        manager = InferenceManager(method="vllm")
        manager.method, manager.model = "hf", model
        self._model = manager
        return self._model

    def extract(self, file_path: Path) -> dict[str, Any]:
        """Extract structured clinical JSON from a PDF or image file."""
        if not self.supports(file_path):
            raise ValueError(f"Unsupported file format {file_path.suffix} for Lift extraction.")

        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check for fast mock mode (used for testing and CPU development)
        if self.mock:
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
            self._release_model()

        return validate_lift_payload(raw_output)

    def _release_model(self) -> None:
        """Free lift's VRAM after each document.

        Quantized lift peaks at ~6.5GiB; the backend also keeps MedCPT, the
        reranker and BART-MNLI resident (plus Ollama's model), so holding lift
        permanently on an 8GB GPU OOMs chat. Uploads are rare, so we pay the
        ~1 min reload instead.
        """
        import gc

        import torch

        self._model = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

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
