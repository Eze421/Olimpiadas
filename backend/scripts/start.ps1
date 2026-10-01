$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

if (-not (Test-Path '.venv\Scripts\python.exe')) { throw 'Falta .venv. Ejecuta: py -m venv .venv' }

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
