#!/usr/bin/env bash
# Start all services (Postgres, Ollama, backend, frontend) via Docker Compose.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker compose -f docker/docker-compose.yml up -d --build
echo "==> Backend:  http://localhost:${BACKEND_PORT:-8000}"
echo "==> Frontend: http://localhost:${FRONTEND_PORT:-3000}"
echo "==> Ollama:   http://localhost:${OLLAMA_PORT:-11434}"
