#!/usr/bin/env bash
# Install dependencies for all subsystems and copy env templates.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

[ -f .env ] || cp .env.example .env
[ -f backend/.env ] || cp backend/.env.example backend/.env
[ -f frontend/.env ] || [ ! -f frontend/.env.example ] || cp frontend/.env.example frontend/.env

echo "==> Backend: Python venv + requirements"
python3 -m venv backend/.venv
backend/.venv/bin/pip install --upgrade pip -q
backend/.venv/bin/pip install -q -r backend/requirements.txt

echo "==> ML: requirements (into the same venv, backend calls into ml/)"
backend/.venv/bin/pip install -q -r ml/requirements.txt

echo "==> Frontend: npm install"
(cd frontend && npm install)

echo "==> Done. Edit .env / backend/.env / frontend/.env, then run scripts/run.sh"
