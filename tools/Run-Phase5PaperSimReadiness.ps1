Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $root

Write-Host "[PHASE-5 PAPER] Phase-5 paper sim readiness check" -ForegroundColor Cyan

$env:PYTHONPATH = Join-Path (Get-Location) "src"
$python = ".\.venv\Scripts\python.exe"

# 1) Import execution_engine and Phase-5 guard modules
Write-Host "`n[PHASE-5 PAPER] Step 1: Import execution_engine + phase5 guard modules" -ForegroundColor Cyan
& $python -c "import hybrid_ai_trading.execution.execution_engine; import hybrid_ai_trading.execution.execution_engine_phase5_guard"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[PHASE-5 PAPER] ERROR: Python import of execution_engine or guard failed." -ForegroundColor Red
    exit 1
}

# 2) NVDA phase5 paper-without-IBG module: import-only (non-destructive)
Write-Host "`n[PHASE-5 PAPER] Step 2: Import tools.paper_live_without_ibg_nvda_phase5 (non-destructive)" -ForegroundColor Cyan

& $python -c "import tools.paper_live_without_ibg_nvda_phase5"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[PHASE-5 PAPER] ERROR: Import of tools.paper_live_without_ibg_nvda_phase5 failed." -ForegroundColor Red
    exit 1
} else {
    Write-Host "[PHASE-5 PAPER] NVDA paper-live module import OK." -ForegroundColor Green
}

# 3) Run Phase-5 tests again as backstop
Write-Host "`n[PHASE-5 PAPER] Step 3: Run Phase-5 test harness as backstop" -ForegroundColor Cyan
$testScript = Join-Path "tools" "Run-Phase5Tests.ps1"
$code = 0
if (Test-Path $testScript) {
    & $testScript
    $code = $LASTEXITCODE
} else {
    Write-Host "[PHASE-5 PAPER] ERROR: Run-Phase5Tests.ps1 not found." -ForegroundColor Red
    $code = 1
}

Write-Host ""
if ($code -eq 0) {
    Write-Host "[PHASE-5 PAPER] Phase-5 paper sim readiness PASSED (imports + tests)." -ForegroundColor Green
} else {
    Write-Host "[PHASE-5 PAPER] Phase-5 paper sim readiness FAILED (tests exit code = $code)." -ForegroundColor Red
}

exit $code