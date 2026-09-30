#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .run/api.pid ]]; then
  PID="$(<.run/api.pid)"
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "API detenida."
  fi
  rm -f .run/api.pid
fi

if command -v podman >/dev/null 2>&1 && podman container exists olimpiadas-postgres; then
  podman stop olimpiadas-postgres >/dev/null
  echo "PostgreSQL detenido; sus datos permanecen en el volumen."
fi
