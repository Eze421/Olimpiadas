#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -x .venv/bin/python ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Error: no se encontró Python."
  exit 1
fi

"$PYTHON_BIN" -m app.seed

# Render provee PORT y necesita que el proceso web quede en primer plano.
# No se usa --reload en producción: evita reinicios y consumo innecesario.
if [[ -n "${PORT:-}" ]]; then
  exec "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
fi

if [[ -f .run/api.pid ]] && kill -0 "$(<.run/api.pid)" 2>/dev/null; then
  echo "La API ya está ejecutándose en http://127.0.0.1:8000"
  exit 0
fi

mkdir -p .run
nohup "$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload > .run/api.log 2>&1 &
echo $! > .run/api.pid
echo "Listo: API en http://127.0.0.1:8000/docs"
echo "Registro: $ROOT_DIR/.run/api.log"
