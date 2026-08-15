"""
Thin wrapper around the local Ollama API.

Responsibilities (to implement):
- Send prompts to the locally-running Ollama model and stream responses
  back. Model is configurable (default: medgemma:8b-q4_0; alternatives:
  qwen2:7b-instruct-q4_0, meditron:7b-q4_0).
- No network calls beyond localhost/the local Ollama instance — the
  privacy boundary is enforced here.
"""
