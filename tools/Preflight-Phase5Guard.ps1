[CmdletBinding()]
param(
    [string]$DateTag = (Get-Date -Format 'yyyyMMdd')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptRoot = $PSScriptRoot
$repoRoot   = Split-Path -Parent $scriptRoot
Set-Location $repoRoot

$py          = '.venv\Scripts\python.exe'
$preflightPy = 'src\hybrid_ai_trading\utils\preflight.py'

if (-not (Test-Path $py)) {
    throw "Python not found: $py"
}
if (-not (Test-Path $preflightPy)) {
    throw "preflight.py not found: $preflightPy"
}

Write-Host "=== Phase5 Preflight Guard ===" -ForegroundColor Cyan
Write-Host "Repo    : $repoRoot"
Write-Host "DateTag : $DateTag"
Write-Host ""

# Call preflight for session/calendar guard
& $py $preflightPy --check-session --date $DateTag
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "[PHASE5-PREFLIGHT] Session not open or preflight failed (exit=$exitCode). Aborting Phase5 run." -ForegroundColor Yellow
    exit 1
}

Write-Host "[PHASE5-PREFLIGHT] Preflight OK; session open and calendar allowed." -ForegroundColor Green