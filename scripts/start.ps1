$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

if (-not (Get-Command podman -ErrorAction SilentlyContinue)) { throw 'Se necesita Podman instalado.' }
if (-not (Test-Path '.venv\Scripts\python.exe')) { throw 'Falta .venv. Ejecuta: py -m venv .venv' }

podman container exists olimpiadas-postgres
if ($LASTEXITCODE -ne 0) {
    podman run -d --name olimpiadas-postgres --label app=olimpiadas -e POSTGRES_DB=olimpiadas -e POSTGRES_USER=olimpiadas -e POSTGRES_PASSWORD=olimpiadas -p 127.0.0.1:5432:5432 -v olimpiadas_postgres_data:/var/lib/postgresql/data docker.io/library/postgres:16-alpine
} elseif ((podman inspect -f '{{.State.Running}}' olimpiadas-postgres) -ne 'true') {
    podman start olimpiadas-postgres
}

Write-Host 'Esperando PostgreSQL...'
for ($i = 0; $i -lt 30; $i++) {
    podman exec olimpiadas-postgres pg_isready -U olimpiadas -d olimpiadas *> $null
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 1
}
podman exec olimpiadas-postgres pg_isready -U olimpiadas -d olimpiadas *> $null
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL no respondió a tiempo.' }

& .venv\Scripts\python.exe -m app.seed
New-Item -ItemType Directory -Force -Path .run | Out-Null
if (Test-Path .run\api.pid) {
    $existingPid = Get-Content .run\api.pid
    if (Get-Process -Id $existingPid -ErrorAction SilentlyContinue) {
        Write-Host 'La API ya está ejecutándose en http://127.0.0.1:8000'
        exit 0
    }
}

$process = Start-Process -FilePath '.venv\Scripts\python.exe' -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000' -RedirectStandardOutput '.run\api.log' -RedirectStandardError '.run\api-error.log' -PassThru
$process.Id | Set-Content .run\api.pid
Write-Host 'Listo: API en http://127.0.0.1:8000/docs'
