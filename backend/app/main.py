"""
FastAPI application entry point.

Responsibilities (to implement):
- Instantiate the FastAPI app and configure CORS/middleware for the
  local-only frontend (no public internet exposure by default).
- Register routers: documents, observations, chat, search, health.
- Wire startup/shutdown hooks: open the PostgreSQL connection pool, verify
  the local Ollama endpoint is reachable, and initialize the vector store
  client.
- No request-handling logic belongs here — this file only assembles the app.
"""
