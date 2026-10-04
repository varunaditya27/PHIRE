import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import torch

from ml.rag.ingest.lift_extractor import LiftExtractor, SUPPORTED_EXTENSIONS
from ml.rag.ingest.lift_schema import CLINICAL_DOCUMENT_SCHEMA, validate_lift_payload



def test_supported_extensions():
    assert ".pdf" in SUPPORTED_EXTENSIONS
    assert ".png" in SUPPORTED_EXTENSIONS
    assert ".jpg" in SUPPORTED_EXTENSIONS
    assert ".jpeg" in SUPPORTED_EXTENSIONS
    assert ".webp" in SUPPORTED_EXTENSIONS


def test_supports_method():
    extractor = LiftExtractor()
    assert extractor.supports(Path("report.pdf"))
    assert extractor.supports(Path("test.png"))
    assert extractor.supports(Path("scan.jpeg"))
    assert extractor.supports(Path("photo.jpg"))
    assert extractor.supports(Path("figure.webp"))
    # Case insensitivity
    assert extractor.supports(Path("REPORT.PDF"))
    assert extractor.supports(Path("SCAN.PNG"))
    assert not extractor.supports(Path("data.csv"))
    assert not extractor.supports(Path("notes.txt"))


def test_mock_extraction(monkeypatch, tmp_path):
    monkeypatch.setenv("PHIRE_MOCK_LIFT", "true")
    dummy_file = tmp_path / "lab.pdf"
    dummy_file.write_bytes(b"%PDF-1.4 dummy")

    extractor = LiftExtractor()
    result = extractor.extract(dummy_file)

    assert "observations" in result
    assert "medications" in result
    assert "conditions" in result
    assert isinstance(result["observations"], list)
    assert isinstance(result["medications"], list)
    assert isinstance(result["conditions"], list)
    assert "narrative_sections" in result
    assert result["document_type"] == "Diagnostic Laboratory Report"

    # Must pass validation cleanly
    validated = validate_lift_payload(result)
    assert len(validated["observations"]) >= 3
    assert len(validated["medications"]) >= 1
    assert len(validated["conditions"]) >= 2


def test_mock_extraction_truthy_flags(monkeypatch, tmp_path):
    dummy_file = tmp_path / "doc.pdf"
    dummy_file.write_bytes(b"dummy")

    for flag in ("1", "yes", "True", "TRUE"):
        monkeypatch.setenv("PHIRE_MOCK_LIFT", flag)
        res = LiftExtractor().extract(dummy_file)
        assert len(res["observations"]) > 0


def test_mock_parameter_enables_mock_mode_without_env_var(monkeypatch, tmp_path):
    monkeypatch.delenv("PHIRE_MOCK_LIFT", raising=False)
    dummy_file = tmp_path / "lab.pdf"
    dummy_file.write_bytes(b"%PDF-1.4 dummy")

    extractor = LiftExtractor(mock=True)
    assert extractor.mock is True
    result = extractor.extract(dummy_file)
    assert result["document_type"] == "Diagnostic Laboratory Report"
    assert len(result["observations"]) > 0


def test_unsupported_file_extension_raises(tmp_path):
    dummy_file = tmp_path / "table.csv"
    dummy_file.write_text("col1,col2\n1,2")
    extractor = LiftExtractor()

    with pytest.raises(ValueError, match="Unsupported file format"):
        extractor.extract(dummy_file)


def test_nonexistent_file_raises_file_not_found(tmp_path):
    missing_file = tmp_path / "missing.pdf"
    extractor = LiftExtractor()

    with pytest.raises(FileNotFoundError, match="File not found"):
        extractor.extract(missing_file)


def test_nonexistent_file_raises_file_not_found_even_in_mock_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("PHIRE_MOCK_LIFT", "true")
    missing_file = tmp_path / "missing.pdf"
    extractor = LiftExtractor()

    with pytest.raises(FileNotFoundError, match="File not found"):
        extractor.extract(missing_file)


def _fake_lift():
    """Stub lift.model / lift.settings so _get_model never loads real weights."""
    manager_cls = MagicMock()
    lift_mod = types.ModuleType("lift")
    lift_model_mod = types.ModuleType("lift.model")
    lift_model_mod.InferenceManager = manager_cls
    lift_settings_mod = types.ModuleType("lift.settings")
    lift_settings_mod.settings = types.SimpleNamespace(MODEL_CHECKPOINT=None, TORCH_DEVICE=None)
    modules = {"lift": lift_mod, "lift.model": lift_model_mod, "lift.settings": lift_settings_mod}
    return manager_cls, lift_settings_mod.settings, modules


def test_get_model_raises_import_error_when_lift_not_installed():
    extractor = LiftExtractor()
    with patch.dict(sys.modules, {"lift": None, "lift.model": None}):
        with pytest.raises(ImportError, match="lift-pdf package not installed"):
            extractor._get_model()


def test_get_model_cuda_loads_4bit_nf4_and_injects_into_manager():
    extractor = LiftExtractor(model_id="datalab-to/lift", device="auto")
    manager_cls, lift_settings, modules = _fake_lift()

    with patch.dict(sys.modules, modules), patch.object(torch.cuda, "is_available", return_value=True):
        with patch("transformers.AutoModelForImageTextToText.from_pretrained") as load, patch(
            "transformers.AutoProcessor.from_pretrained"
        ):
            manager = extractor._get_model()

    kwargs = load.call_args.kwargs
    cfg = kwargs["quantization_config"]
    assert cfg.load_in_4bit is True
    assert cfg.bnb_4bit_quant_type == "nf4"
    assert cfg.bnb_4bit_compute_dtype == torch.bfloat16
    assert cfg.llm_int8_skip_modules == ["visual"]
    assert kwargs["device_map"] == {"": 0}
    # The quantized model is injected; lift's own bf16 loader never runs.
    manager_cls.assert_called_once_with(method="vllm")
    assert manager is manager_cls.return_value
    assert manager.method == "hf"
    assert manager.model is load.return_value.eval.return_value
    assert lift_settings.MODEL_CHECKPOINT == "datalab-to/lift"


def test_get_model_cuda_failure_does_not_fall_back_to_unquantized():
    extractor = LiftExtractor(device="cuda")
    manager_cls, _, modules = _fake_lift()

    with patch.dict(sys.modules, modules), patch.object(torch.cuda, "is_available", return_value=True):
        with patch(
            "transformers.AutoModelForImageTextToText.from_pretrained",
            side_effect=RuntimeError("bnb load failed"),
        ):
            with pytest.raises(RuntimeError, match="bnb load failed"):
                extractor._get_model()
    manager_cls.assert_not_called()


@pytest.mark.parametrize("device,cuda_available", [("auto", False), ("cpu", True)])
def test_get_model_cpu_uses_lift_default_loader_without_quantization(device, cuda_available):
    extractor = LiftExtractor(device=device)
    manager_cls, lift_settings, modules = _fake_lift()

    with patch.dict(sys.modules, modules), patch.object(
        torch.cuda, "is_available", return_value=cuda_available
    ):
        with patch("transformers.AutoModelForImageTextToText.from_pretrained") as load:
            manager = extractor._get_model()

    load.assert_not_called()
    manager_cls.assert_called_once_with(method="hf")
    assert manager is manager_cls.return_value
    assert lift_settings.TORCH_DEVICE == "cpu"


def test_real_extract_call_flow(tmp_path, monkeypatch):
    monkeypatch.delenv("PHIRE_MOCK_LIFT", raising=False)
    dummy_file = tmp_path / "report.pdf"
    dummy_file.write_bytes(b"%PDF-1.4 dummy")

    mock_extract_fn = MagicMock(return_value={
        "document_date": "2026-01-01",
        "document_type": "Blood Test",
        "observations": [{"name": "Glucose", "value": "95", "unit": "mg/dL"}],
        "medications": [],
        "conditions": [],
        "narrative_sections": [],
    })
    mock_inference_manager = MagicMock()
    lift_mod = types.ModuleType("lift")
    lift_model_mod = types.ModuleType("lift.model")
    lift_model_mod.InferenceManager = mock_inference_manager
    lift_mod.extract = mock_extract_fn
    lift_mod.model = lift_model_mod

    with patch.dict(sys.modules, {"lift": lift_mod, "lift.model": lift_model_mod}):
        extractor = LiftExtractor()
        model_stub = extractor._model = mock_inference_manager.return_value  # skip real model loading
        with patch.object(torch.cuda, "is_available", return_value=True), \
             patch.object(torch.cuda, "empty_cache") as mock_empty_cache:
            res = extractor.extract(dummy_file)
            assert res["document_type"] == "Blood Test"
            assert res["observations"][0]["name"] == "Glucose"
            mock_extract_fn.assert_called_once_with(
                str(dummy_file),
                CLINICAL_DOCUMENT_SCHEMA,
                model=model_stub,
            )
            mock_empty_cache.assert_called_once()


def test_real_extract_result_object_with_extraction_attr(tmp_path, monkeypatch):
    monkeypatch.delenv("PHIRE_MOCK_LIFT", raising=False)
    dummy_file = tmp_path / "report.png"
    dummy_file.write_bytes(b"dummy image bytes")

    class LiftResult:
        def __init__(self, data):
            self.extraction = data

    payload = {
        "document_date": "2026-02-02",
        "document_type": "Image Report",
        "observations": [{"name": "HbA1c", "value": "5.6", "unit": "%"}],
        "medications": [],
        "conditions": [],
        "narrative_sections": [],
    }

    mock_extract_fn = MagicMock(return_value=LiftResult(payload))
    mock_inference_manager = MagicMock()
    lift_mod = types.ModuleType("lift")
    lift_model_mod = types.ModuleType("lift.model")
    lift_model_mod.InferenceManager = mock_inference_manager
    lift_mod.extract = mock_extract_fn
    lift_mod.model = lift_model_mod

    with patch.dict(sys.modules, {"lift": lift_mod, "lift.model": lift_model_mod}):
        extractor = LiftExtractor()
        model_stub = extractor._model = mock_inference_manager.return_value  # skip real model loading
        with patch.object(torch.cuda, "is_available", return_value=False):
            res = extractor.extract(dummy_file)
            assert res["document_type"] == "Image Report"
            assert res["observations"][0]["name"] == "HbA1c"
            mock_extract_fn.assert_called_once_with(
                str(dummy_file),
                CLINICAL_DOCUMENT_SCHEMA,
                model=model_stub,
            )


def test_real_extract_raises_runtime_error_on_failure(tmp_path, monkeypatch):
    monkeypatch.delenv("PHIRE_MOCK_LIFT", raising=False)
    dummy_file = tmp_path / "corrupt.pdf"
    dummy_file.write_bytes(b"corrupt")

    mock_extract_fn = MagicMock(side_effect=Exception("CUDA out of memory"))
    mock_inference_manager = MagicMock()
    lift_mod = types.ModuleType("lift")
    lift_model_mod = types.ModuleType("lift.model")
    lift_model_mod.InferenceManager = mock_inference_manager
    lift_mod.extract = mock_extract_fn
    lift_mod.model = lift_model_mod

    with patch.dict(sys.modules, {"lift": lift_mod, "lift.model": lift_model_mod}):
        extractor = LiftExtractor()
        model_stub = extractor._model = mock_inference_manager.return_value  # skip real model loading
        with patch.object(torch.cuda, "is_available", return_value=True), \
             patch.object(torch.cuda, "empty_cache") as mock_empty_cache:
            with pytest.raises(RuntimeError, match="Lift extraction failed"):
                extractor.extract(dummy_file)
            mock_extract_fn.assert_called_once_with(
                str(dummy_file),
                CLINICAL_DOCUMENT_SCHEMA,
                model=model_stub,
            )
            mock_empty_cache.assert_called_once()

