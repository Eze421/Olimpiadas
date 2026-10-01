#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v podman >/dev/null 2>&1; then
  echo "Error: se necesita Podman instalado."
  exit 1
fi
if [[ ! -x .venv/bin/python ]]; then
  echo "Error: falta el entorno virtual. Ejecutá: python3 -m venv .venv"
  exit 1
fi

if ! podman container exists olimpiadas-postgres; then
  podman run -d --name olimpiadas-postgres --label app=olimpiadas \
    -e POSTGRES_DB=olimpiadas -e POSTGRES_USER=olimpiadas -e POSTGRES_PASSWORD=olimpiadas \
    -p 127.0.0.1:5432:5432 \
    -v olimpiadas_postgres_data:/var/lib/postgresql/data:Z \
    docker.io/library/postgres:16-alpine
elif [[ "$(podman inspect -f '{{.State.Running}}' olimpiadas-postgres)" != "true" ]]; then
  podman start olimpiadas-postgres
fi

echo "Esperando PostgreSQL..."
for _ in {1..30}; do
  if podman exec olimpiadas-postgres pg_isready -U olimpiadas -d olimpiadas >/dev/null 2>&1; then break; fi
  sleep 1
done
podman exec olimpiadas-postgres pg_isready -U olimpiadas -d olimpiadas >/dev/null

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
