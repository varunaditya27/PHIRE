#!/usr/bin/env bash
# Run the Next.js frontend locally (no Docker).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../frontend"
exec npm run dev
