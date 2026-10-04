#!/usr/bin/env bash
# Start the whole PHIRE stack (Postgres, Neo4j, backend, frontend, + Ollama if the host has none) with Docker Compose.
#
#   scripts/run.sh                 # build + start, wait until the backend is healthy
#   scripts/run.sh --profile proxy # extra args go to `docker compose` (e.g. the nginx proxy)
#   (uses the host's Ollama if one is running; otherwise starts the bundled Ollama container)
#   scripts/run.sh down            # stop (data volumes and data/ are kept)
#
# Uses the root .env explicitly (Compose would otherwise read docker/.env and ignore it) and
# layers docker/docker-compose.gpu.yml when an NVIDIA container runtime is available, otherwise
# docker/docker-compose.cpu.yml (override with PHIRE_VARIANT=gpu|cpu).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

[ -f .env ] || { cp .env.example .env; echo "==> Created .env from .env.example (edit passwords/ports as needed)"; }
[ -f backend/.env ] || { cp backend/.env.example backend/.env; echo "==> Created backend/.env from backend/.env.example"; }
set -a; source .env; set +a

# GPU or CPU variant: PHIRE_VARIANT=gpu|cpu forces one; otherwise an NVIDIA container runtime means GPU.
files=(-f docker/docker-compose.yml)
variant="${PHIRE_VARIANT:-auto}"
if [ "$variant" = "auto" ]; then
  if docker info 2>/dev/null | grep -qi 'runtimes:.*nvidia'; then variant=gpu; else variant=cpu; fi
fi
if [ "$variant" = "gpu" ]; then
  files+=(-f docker/docker-compose.gpu.yml)
  echo "==> GPU variant: NVIDIA runtime in use for the backend (lift extraction) and any bundled Ollama"
else
  files+=(-f docker/docker-compose.cpu.yml)
  echo "==> CPU variant: CPU-only PyTorch, documents read by an Ollama vision model (slower; see docs/CPU_SETUP.md)"
fi

# The backend uses the Ollama already running on the host. Only fall back to the bundled container
# (profile `ollama`) when there is none, so we never pull a second copy of the model.
ollama_url="${OLLAMA_HOST:-http://localhost:${OLLAMA_PORT:-11434}}"
profiles=()
if tags=$(curl -fs "$ollama_url/api/tags" 2>/dev/null); then
  echo "==> Using host Ollama at $ollama_url"
  grep -q "\"${OLLAMA_MODEL:-medgemma:4b}\"" <<<"$tags" \
    || echo "    WARNING: model ${OLLAMA_MODEL:-medgemma:4b} not found there -- run: ollama pull ${OLLAMA_MODEL:-medgemma:4b}" >&2
else
  echo "==> No Ollama at $ollama_url: starting the bundled container (it will pull ${OLLAMA_MODEL:-medgemma:4b})"
  profiles=(--profile ollama)
fi
compose=(docker compose --env-file .env "${files[@]}" "${profiles[@]}")

if [ "${1:-}" = "down" ]; then
  exec "${compose[@]}" down
fi

mkdir -p "${PHIRE_DATA_DIR:-data}"  # created as you, not root, so the container user can write to it
"${compose[@]}" "$@" up -d --build

port="${BACKEND_PORT:-8000}"
echo "==> Waiting for the backend (first start downloads the chat model; this can take several minutes)..."
for _ in $(seq 1 180); do
  curl -fs "http://127.0.0.1:${port}/api/ping" >/dev/null 2>&1 && break
  sleep 5
done
curl -fs "http://127.0.0.1:${port}/api/ping" >/dev/null 2>&1 || { echo "Backend not healthy yet: docker compose logs backend" >&2; exit 1; }

echo "==> Frontend: http://localhost:${FRONTEND_PORT:-3000}"
echo "==> Backend:  http://localhost:${port}   (API docs: /docs)"
echo "==> First time? Seed the public reference corpus once:"
echo "    docker compose --env-file .env ${files[*]} --profile ingest run --rm ingest"
