param(
    [Parameter(Mandatory = $false)][string] $Symbol,
    [Parameter(Mandatory = $false)][string] $Session,
    [Parameter(Mandatory = $false)][string] $SummaryJson = ""
)

$ErrorActionPreference = 'Stop'

# Determine repo root (supports both script + interactive)
if ($MyInvocation.MyCommand.Path) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $repoRoot  = Resolve-Path (Join-Path $scriptDir '..')
} else {
    $repoRoot = Get-Location
}

Set-Location $repoRoot

# Python env for OneTap
$PythonExe      = '.\.venv\Scripts\python.exe'
$env:PYTHONPATH = (Join-Path $repoRoot 'src')

# === Phase-5 guardrails: microsuites + PreMarket-Check =======================
Write-Host "[ONETAP] Phase-5 guardrails: microsuites + PreMarket-Check..." -ForegroundColor Cyan

try {
    Write-Host "[ONETAP] Running Phase-5 risk microsuite..." -ForegroundColor Cyan
    .\tools\Run-Phase5Tests.ps1
    Write-Host "[ONETAP] Phase-5 risk microsuite: OK" -ForegroundColor Green
}
catch {
    Write-Host "[ONETAP] Phase-5 risk microsuite: FAILED - aborting PreMarket-OneTap" -ForegroundColor Red
    throw
}

try {
    Write-Host "[ONETAP] Running portfolio/exec microsuite..." -ForegroundColor Cyan
    .\tools\Run-PortfolioExecTests.ps1
    Write-Host "[ONETAP] Portfolio/exec microsuite: OK" -ForegroundColor Green
}
catch {
    Write-Host "[ONETAP] Portfolio/exec microsuite: FAILED - aborting PreMarket-OneTap" -ForegroundColor Red
    throw
}

try {
    Write-Host "[ONETAP] Running PreMarket-Check.ps1 (RiskPulse + QoS)..." -ForegroundColor Cyan
    .\tools\PreMarket-Check.ps1
    Write-Host "[ONETAP] PreMarket-Check.ps1: OK_TO_TRADE" -ForegroundColor Green
}
catch {
    Write-Host "[ONETAP] PreMarket-Check.ps1 FAILED - aborting PreMarket-OneTap" -ForegroundColor Red
    throw
}
# ============================================================================

# If no symbol/session provided, run in GUARDRAILS-ONLY mode
if (-not $Symbol -or -not $Session) {
    Write-Host "[ONETAP] No -Symbol / -Session provided -> guardrails-only mode (Python runner skipped)." -ForegroundColor Yellow
    Write-Host "[ONETAP] Use: .\tools\PreMarket-OneTap.ps1 -Symbol NVDA -Session 2025-11-19" -ForegroundColor Yellow
    exit 0
}

# === Launch Python OneTap runner ============================================
Write-Host "[ONETAP] Launching Python PreMarket-OneTap.py for Symbol=$Symbol Session=$Session ..." -ForegroundColor Cyan

$pyArgs = @('.\tools\PreMarket-OneTap.py', '--symbol', $Symbol, '--session', $Session)

if ($SummaryJson) {
    $pyArgs += @('--summary-json', $SummaryJson)
}

& $PythonExe @pyArgs
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "[ONETAP] Python OneTap runner exited with code $exitCode" -ForegroundColor Red
    exit $exitCode
}

Write-Host "[ONETAP] PreMarket-OneTap complete (exit 0)" -ForegroundColor Green
exit 0