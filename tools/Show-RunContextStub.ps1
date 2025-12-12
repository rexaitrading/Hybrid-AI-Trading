[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsPath = Join-Path $repoRoot "logs"

# Assume stub JSON lives under logs\runcontext_phase5_stub.json (adjust if needed)
$stubJson = Join-Path $logsPath "runcontext_phase5_stub.json"

if (-not (Test-Path $stubJson)) {
    Write-Host "[RUNCTX] Stub JSON not found at $stubJson" -ForegroundColor Yellow
    Write-Host "[RUNCTX] Running Build-RunContextStub.ps1 via Run-BlockGReadiness harness first..." -ForegroundColor Yellow
    if (Test-Path (Join-Path $toolsDir "Run-BlockGReadiness.ps1")) {
        & (Join-Path $toolsDir "Run-BlockGReadiness.ps1") | Out-Null
    }
}

if (-not (Test-Path $stubJson)) {
    Write-Host "[RUNCTX] Still no stub JSON; please confirm Build-RunContextStub.ps1 output path." -ForegroundColor Red
    return
}

Write-Host "[RUNCTX] Current RunContext stub:" -ForegroundColor Cyan
Get-Content $stubJson

