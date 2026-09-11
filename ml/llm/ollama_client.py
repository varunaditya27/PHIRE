"""
Thin wrapper around the local Ollama API.

Enforces PHIRE's local-only boundary at the code level, not just by
convention: the host must resolve to localhost, so this client can never
be pointed at a remote Ollama instance by a stray config value.
"""

import os

import requests

from ml.local_only import require_localhost

DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "medgemma:4b")


class OllamaClient:
    """Sends prompts to a local Ollama model and returns its completion."""

    def __init__(self, model: str | None = None, host: str | None = None, timeout: float = 180.0) -> None:
        self.model = model or DEFAULT_MODEL
        self.host = host or DEFAULT_HOST
        self.timeout = timeout
        require_localhost(self.host)

    def generate(
        self, prompt: str, system: str | None = None, temperature: float = 0.2, max_tokens: int = 1024
    ) -> str:
        """Non-streaming completion via Ollama's /api/generate endpoint.

        max_tokens (Ollama's num_predict) caps worst-case latency: without
        it, a request that never emits a stop token (found live -- one
        such request sat for 10 minutes before Ollama itself gave up and
        errored) has no bound at all, and self.timeout only cuts the
        client off after the fact rather than bounding what Ollama itself
        will attempt. 1024 is generous for a chat answer or a JSON claims
        list; callers with a much shorter expected output (e.g. claim
        extraction) should pass a tighter value.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system:
            payload["system"] = system
        response = requests.post(f"{self.host}/api/generate", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()["response"]
