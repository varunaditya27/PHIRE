"""Unit tests for backend/app/services/gpu_modes.py's LIFT/CHAT residency switching (no real GPU or models)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

backend_path = str(Path(__file__).resolve().parents[2] / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services import gpu_modes
from app.services.gpu_modes import CHAT, LIFT, gpu_mode


class FakeGetter:
    """Stands in for an @lru_cache singleton getter: built or not, with a recording model."""

    def __init__(self, built: bool) -> None:
        self.model = MagicMock()
        self._built = built

    def cache_info(self):
        return MagicMock(currsize=1 if self._built else 0)

    def __call__(self):
        return self.model


@pytest.fixture
def env(monkeypatch):
    built, unbuilt = FakeGetter(True), FakeGetter(False)
    monkeypatch.setattr(gpu_modes, "_CHAT_MODELS", (built, unbuilt))
    monkeypatch.setattr(gpu_modes, "_current", None)
    lift = FakeGetter(True)
    monkeypatch.setattr(gpu_modes.ml, "get_lift_extractor", lift)
    with patch.object(gpu_modes, "_unload_ollama_model") as unload, patch.object(
        gpu_modes.torch.cuda, "is_available", return_value=True
    ), patch.object(gpu_modes.torch.cuda, "empty_cache"):
        yield built, unbuilt, lift, unload


def test_entering_lift_parks_built_chat_models_on_cpu_and_unloads_ollama(env):
    built, unbuilt, _, unload = env
    with gpu_mode(LIFT):
        pass
    built.model.move_to.assert_called_once_with("cpu")
    unbuilt.model.move_to.assert_not_called()  # never builds a singleton just to move it
    unload.assert_called_once()


def test_returning_to_chat_releases_lift_and_restores_chat_models(env):
    built, _, lift, _ = env
    with gpu_mode(LIFT):
        pass
    with gpu_mode(CHAT):
        pass
    lift.model._release_model.assert_called_once()
    assert built.model.move_to.call_args_list[-1].args == ("cuda",)


def test_same_mode_twice_is_a_no_op(env):
    built, _, lift, unload = env
    with gpu_mode(CHAT):
        pass
    moves_after_first = built.model.move_to.call_count
    with gpu_mode(CHAT):
        pass
    assert built.model.move_to.call_count == moves_after_first
    assert lift.model._release_model.call_count == 1
    unload.assert_not_called()
