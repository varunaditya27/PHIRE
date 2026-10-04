"""get_extractor() picks lift on a CUDA GPU and the Ollama vision model otherwise (backend/app/services/ml_singletons.py)."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

backend_path = str(Path(__file__).resolve().parents[2] / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services import ml_singletons as ml


@pytest.fixture(autouse=True)
def _fresh_caches():
    ml.get_ollama_extractor.cache_clear()
    ml.get_lift_extractor.cache_clear()
    yield
    ml.get_ollama_extractor.cache_clear()
    ml.get_lift_extractor.cache_clear()


def _select(choice, lift_usable):
    settings = SimpleNamespace(phire_extractor=choice, ollama_vision_model=None, ollama_model="medgemma:4b",
                               ollama_host="http://localhost:11434", lift_model="datalab-to/lift", lift_device="auto", phire_mock_lift=True)
    with patch.object(ml, "get_settings", return_value=settings), patch.object(ml, "_lift_usable", return_value=lift_usable):
        return ml.get_extractor()


def test_auto_uses_lift_when_a_gpu_and_lift_are_available():
    assert _select("auto", True).gpu_mode == "lift"


def test_auto_falls_back_to_the_ollama_vision_model_without_a_gpu():
    extractor = _select("auto", False)

    assert extractor.gpu_mode == "chat" and extractor.model == "medgemma:4b"


def test_ollama_can_be_forced_even_on_a_gpu_machine():
    assert _select("ollama", True).gpu_mode == "chat"


def test_lift_can_be_forced_and_unknown_values_are_rejected():
    assert _select("lift", False).gpu_mode == "lift"
    with pytest.raises(ValueError, match="auto, lift or ollama"):
        _select("banana", True)
