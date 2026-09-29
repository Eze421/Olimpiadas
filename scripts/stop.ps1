$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

if (Test-Path .run\api.pid) {
    $apiPid = Get-Content .run\api.pid
    Stop-Process -Id $apiPid -Force -ErrorAction SilentlyContinue
    Remove-Item .run\api.pid -Force
    Write-Host 'API detenida.'
}
if (Get-Command podman -ErrorAction SilentlyContinue) {
    podman container exists olimpiadas-postgres
    if ($LASTEXITCODE -eq 0) {
        podman stop olimpiadas-postgres | Out-Null
        Write-Host 'PostgreSQL detenido; sus datos permanecen en el volumen.'
    }
}
