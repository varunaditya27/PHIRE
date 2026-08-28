#!/usr/bin/env bash
# Run the FastAPI backend locally (no Docker) — expects Postgres + Ollama
# + Neo4j already reachable per backend/.env.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/backend"

set -a
[ -f .env ] && source .env
set +a

# ml/ lives at the repo root, not under backend/ -- Docker's runtime bind
# mount (../ml:/app/ml, WORKDIR /app) puts it on the import path
# automatically, but a local (non-Docker) uvicorn process started from
# backend/ has no other way to see it. Without this, every
# `import ml....` in app/services/ml_singletons.py raises ModuleNotFoundError
# and every ml/-backed route (chat, search, evidence, claims, documents,
# observations) silently fails (verified live: this is exactly what
# happened before this line was added).
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

.venv/bin/alembic upgrade head
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
