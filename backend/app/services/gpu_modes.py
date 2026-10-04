"""
Two mutually exclusive GPU residency modes for the 8GB card.

LIFT:  only the quantized lift VLM is on the GPU (~6.5GiB peak).
CHAT:  MedCPT embeddings, the reranker, BART-MNLI and Ollama's chat model
       are co-resident (~6.9GiB measured) -- they fit together but not
       beside lift.

gpu_mode() takes the process-wide GPU lock, evicts the *other* group if the
mode changed, and does nothing when the requested mode is already active
(consecutive chats never move a model). Eviction parks in-process models in
CPU RAM (cheap ~1s reload) rather than destroying them; Ollama's model is
unloaded through its API because it lives in another process.
"""

from collections.abc import Callable
from contextlib import contextmanager

import httpx
import torch

from app.config import get_settings
from app.services import ml_singletons as ml

LIFT = "lift"
CHAT = "chat"

_current: str | None = None

# Singletons whose weights sit on the GPU in CHAT mode and expose move_to().
_CHAT_MODELS = (ml.get_retriever, ml.get_reranker, ml.get_claim_verifier)


def _loaded(getter):
    """The cached singleton if it has been built, else None (never builds one)."""
    return getter() if getter.cache_info().currsize else None


def _move_chat_models(device: str) -> None:
    """Move whichever chat-group models already exist; unbuilt ones load on demand."""
    for getter in _CHAT_MODELS:
        model = _loaded(getter)
        if model is not None:
            model.move_to(device)


def _unload_ollama_model() -> None:
    """Evict Ollama's resident chat model; best-effort, a failure only risks tighter VRAM."""
    settings = get_settings()
    try:
        httpx.post(
            f"{settings.ollama_host}/api/generate",
            json={"model": settings.ollama_model, "keep_alive": 0},
            timeout=10,
        )
    except httpx.HTTPError as exc:
        print(f"gpu_modes: could not unload Ollama model: {exc}")


def _switch_to(mode: str, on_progress: Callable[[str, str], None] | None = None) -> None:
    """Evict the other group and bring this one up; no-op if already in `mode`."""
    global _current
    if mode == _current:
        return
    if on_progress:
        on_progress("gpu", f"Loading {'vision' if mode == LIFT else 'chat'} models onto the GPU")
    if mode == LIFT:
        _unload_ollama_model()
        _move_chat_models("cpu")
    else:
        extractor = _loaded(ml.get_lift_extractor)
        if extractor is not None:
            extractor._release_model()
        if torch.cuda.is_available():
            _move_chat_models("cuda")
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    _current = mode


@contextmanager
def gpu_mode(mode: str, on_progress: Callable[[str, str], None] | None = None):
    """Hold the GPU lock with `mode` resident for the duration of the block.

    on_progress(stage, message) reports waiting on another GPU job and the
    mode switch itself, the two silent delays a user would otherwise see as
    a frozen UI.
    """
    if on_progress and ml.GPU_LOCK.locked():
        on_progress("gpu_wait", "Waiting for another GPU task to finish")
    with ml.GPU_LOCK:
        _switch_to(mode, on_progress)
        yield
