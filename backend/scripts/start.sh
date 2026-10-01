#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  echo "Error: falta el entorno virtual. Ejecutá: python3 -m venv .venv"
  exit 1
fi

.venv/bin/python -m app.seed

if [[ -f .run/api.pid ]] && kill -0 "$(<.run/api.pid)" 2>/dev/null; then
  echo "La API ya está ejecutándose en http://127.0.0.1:8000"
  exit 0
fi

mkdir -p .run
nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload > .run/api.log 2>&1 &
echo $! > .run/api.pid
echo "Listo: API en http://127.0.0.1:8000/docs"
echo "Registro: $ROOT_DIR/.run/api.log"
