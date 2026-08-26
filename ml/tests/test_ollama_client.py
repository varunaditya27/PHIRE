"""Unit test for ml/llm/ollama_client.py's localhost enforcement."""

import pytest

from ml.llm.ollama_client import OllamaClient


def test_ollama_client_accepts_localhost_host():
    client = OllamaClient(host="http://localhost:11434")
    assert client.host == "http://localhost:11434"


def test_ollama_client_accepts_loopback_ip_host():
    client = OllamaClient(host="http://127.0.0.1:11434")
    assert client.host == "http://127.0.0.1:11434"


def test_ollama_client_rejects_remote_host():
    with pytest.raises(ValueError, match="localhost"):
        OllamaClient(host="http://some-remote-server.example.com:11434")
