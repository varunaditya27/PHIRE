"""
POST /api/health — service liveness/readiness endpoint.

Responsibilities (to implement):
- Check PostgreSQL connectivity, Ollama reachability, and vector store
  status.
- Used by docker-compose healthchecks and the frontend's system-status
  indicator.
"""
