"""
Thin wrapper around the local Ollama API.

Enforces PHIRE's local-only boundary at the code level, not just by
convention: the host must resolve to localhost, so this client can never
be pointed at a remote Ollama instance by a stray config value.
"""

import os

import requests

DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "medgemma:4b")
_ALLOWED_HOST_PREFIXES = ("http://localhost", "http://127.0.0.1")


class OllamaClient:
    """Sends prompts to a local Ollama model and returns its completion."""

    def __init__(self, model: str | None = None, host: str | None = None) -> None:
        self.model = model or DEFAULT_MODEL
        self.host = host or DEFAULT_HOST
        if not self.host.startswith(_ALLOWED_HOST_PREFIXES):
            raise ValueError(f"OllamaClient only permits a localhost host, got: {self.host}")

    def generate(self, prompt: str, system: str | None = None, temperature: float = 0.2) -> str:
        """Non-streaming completion via Ollama's /api/generate endpoint."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        response = requests.post(f"{self.host}/api/generate", json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["response"]
