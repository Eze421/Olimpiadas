$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

if (Test-Path .run\api.pid) {
    $apiPid = Get-Content .run\api.pid
    Stop-Process -Id $apiPid -Force -ErrorAction SilentlyContinue
    Remove-Item .run\api.pid -Force
    Write-Host 'API detenida.'
}
