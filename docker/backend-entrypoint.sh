#!/bin/sh
# Backend container entrypoint: apply database migrations, then serve.
# Migrations run on every start (`alembic upgrade head` is a no-op when current) so a
# fresh Postgres gets its tables without a manual step. Single uvicorn worker on purpose:
# GPU residency (gpu_modes.py) and SSE progress (progress.py) are per-process state.
set -eu

attempt=1
until alembic upgrade head; do
  if [ "$attempt" -ge 10 ]; then
    echo "backend: database migrations failed after $attempt attempts" >&2
    exit 1
  fi
  attempt=$((attempt + 1))
  echo "backend: database not ready, retrying migrations ($attempt/10)..." >&2
  sleep 3
done

exec uvicorn app.main:app --host "${BACKEND_HOST:-127.0.0.1}" --port "${BACKEND_PORT:-8000}"
