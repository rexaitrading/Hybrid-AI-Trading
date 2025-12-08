[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "`n[PHASE5 PREFLIGHT] === Phase-5 EV + Risk Preflight ===" -ForegroundColor Cyan

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

Set-Location $repoRoot

# --- 1) EV anchor summary (NVDA / SPY / QQQ + EV-bands) ---
$evSummary = Join-Path $toolsDir "Show-Phase5EvAnchors.ps1"
if (Test-Path $evSummary) {
    Write-Host "`n[STEP 1] Phase-5 EV anchor summary" -ForegroundColor Yellow
    & $evSummary
} else {
    Write-Host "[WARN] Show-Phase5EvAnchors.ps1 not found at $evSummary" -ForegroundColor Red
}

# --- 2) Phase-5 PnL/EV audit (if available) ---
$phase5Audit = Join-Path $toolsDir "Run-Phase5Audit.ps1"
if (Test-Path $phase5Audit) {
    Write-Host "`n[STEP 2] Phase-5 PnL/EV audit (NVDA + SPY + QQQ)" -ForegroundColor Yellow
    & $phase5Audit
} else {
    Write-Host "[SKIP] Run-Phase5Audit.ps1 not found at $phase5Audit" -ForegroundColor DarkYellow
}

# --- 3) Phase-5 risk & guard pytest slice ---
Write-Host "`n[STEP 3] Phase-5 risk & guard tests (pytest slice)" -ForegroundColor Yellow

$PythonExe = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Python executable not found at $PythonExe" -ForegroundColor Red
    Write-Host "[PHASE5 PREFLIGHT] ABORT: venv Python missing." -ForegroundColor Red
    exit 1
}

$testFiles = @(
    "tests\test_phase5_riskmanager_combined_gates.py",
    "tests\test_phase5_riskmanager_daily_loss_integration.py",
    "tests\test_phase5_no_averaging_engine_guard.py",
    "tests\test_phase5_ev_bands_basic.py",
    "tests\test_phase5_ev_band_hard_veto.py",
    "tests\test_execution_engine_phase5_guard.py",
    "tests\test_ib_phase5_guard.py"
)

$existingTests = $testFiles | Where-Object { Test-Path $_ }

if ($existingTests.Count -eq 0) {
    Write-Host "[SKIP] No Phase-5 test files found in expected locations." -ForegroundColor DarkYellow
} else {
    & $PythonExe -m pytest @existingTests
}

Write-Host "`n[PHASE5 PREFLIGHT] === End Phase-5 EV + Risk Preflight ===`n" -ForegroundColor Cyan