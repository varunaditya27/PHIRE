"""
Application settings, loaded from environment variables (see .env.example).

Responsibilities (to implement):
- Define a Settings object (e.g. pydantic BaseSettings) covering: database
  URL, Ollama host/model name, vector store connection, allowed CORS
  origins, upload size limits, and encryption keys.
- Single source of truth for config — no other module should read
  os.environ directly.
"""
