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

# --- Phase-5 EV sync gate ---------------------------------------------
# Require a successful Run-Phase5EvSync.ps1 before launching IB paper/live.
try {
    $evStatusPath = Join-Path $repoRoot 'logs\phase5_ev_sync_status.json'
    if (-not (Test-Path $evStatusPath)) {
        Write-Host "[PHASE5-EV] ERROR: phase5_ev_sync_status.json not found. Run Run-Phase5EvSync.ps1 first." -ForegroundColor Red
        return
    }

    $evStatusJson = Get-Content $evStatusPath -Raw
    $evStatus     = $evStatusJson | ConvertFrom-Json

    if (-not $evStatus.success) {
        Write-Host "[PHASE5-EV] ERROR: Last Phase-5 EV sync did not succeed (success=false). Fix EV sync before trading." -ForegroundColor Red
        return
    }

    Write-Host "[PHASE5-EV] EV sync check passed (phase5_ev_sync_status.json success=true)." -ForegroundColor Green
}
catch {
    Write-Host ("[PHASE5-EV] ERROR checking EV sync status: {0}" -f $_.Exception.Message) -ForegroundColor Red
    return
}
# -----------------------------------------------------------------------

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

# --- Phase-5 NVDA IB paper live -------------------------------------------------
Write-Host "`n[PHASE5] NVDA Phase-5 IB paper pipeline (IB paper + CSV)" -ForegroundColor Cyan

# IB connection env (adjust values / pull from your config if needed)
$env:HAT_IB_HOST      = "127.0.0.1"
$env:HAT_IB_PORT      = "7497"
$env:HAT_IB_CLIENT_ID = "42"
$env:HAT_IB_ACCOUNT   = "DUXXXXXXXX"   # TODO: replace with your IB PAPER account code

# Phase-5 daily loss cap (USD)
$env:HAT_PHASE5_ACCOUNT_DAILY_LOSS_CAP = "50"

# Run NVDA Phase-5 paper pipeline (live runner + CSV for Notion)
Write-Host "[PHASE5] Running tools\\Invoke-NvdaPhase5PaperPipeline.ps1..." -ForegroundColor Cyan
.\tools\Invoke-NvdaPhase5PaperPipeline.ps1
# -------------------------------------------------------------------------------

Write-Host "[ONETAP] PreMarket-OneTap complete (exit 0)" -ForegroundColor Green
exit 0
