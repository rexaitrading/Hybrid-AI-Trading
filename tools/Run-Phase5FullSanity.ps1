Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $root

Write-Host "[PHASE-5 FULL] Starting Phase-5 full sanity (ORB + Risk + Tests)" -ForegroundColor Cyan

# 1) ORB Phase-5 dev loop (SPY/QQQ/NVDA ORB risk + CSV + sanity)
Write-Host "`n[PHASE-5 FULL] Step 1: ORB Phase-5 dev sanity (Run-Phase5ORBDev.ps1)" -ForegroundColor Cyan

$orbScript = Join-Path "tools" "Run-Phase5ORBDev.ps1"
if (Test-Path $orbScript) {
    & $orbScript
} else {
    Write-Host "[PHASE-5 FULL] WARNING: $orbScript not found; skipping ORB dev sanity." -ForegroundColor Yellow
}

# 2) Pre-market + Phase-5 ORB sanity (wrapper variant)
Write-Host "`n[PHASE-5 FULL] Step 2: PreMarket-Check-Phase5 (intel + QoS + Phase-5 ORB)" -ForegroundColor Cyan

$preWrapper = Join-Path "tools" "PreMarket-Check-Phase5.ps1"
if (Test-Path $preWrapper) {
    & $preWrapper
} else {
    Write-Host "[PHASE-5 FULL] WARNING: $preWrapper not found; skipping pre-market wrapper." -ForegroundColor Yellow
}

# 3) Phase-5 risk/guard test harness
Write-Host "`n[PHASE-5 FULL] Step 3: Run-Phase5Tests.ps1 (Phase-5 risk / guard test suite)" -ForegroundColor Cyan

$testScript = Join-Path "tools" "Run-Phase5Tests.ps1"
$code = 0
if (Test-Path $testScript) {
    & $testScript
    $code = $LASTEXITCODE
} else {
    Write-Host "[PHASE-5 FULL] ERROR: $testScript not found; cannot run Phase-5 tests." -ForegroundColor Red
    $code = 1
}

Write-Host ""
if ($code -eq 0) {
    Write-Host "[PHASE-5 FULL] Phase-5 full sanity PASSED (ORB + risk + tests)." -ForegroundColor Green
} else {
    Write-Host "[PHASE-5 FULL] Phase-5 full sanity FAILED (tests exit code = $code)." -ForegroundColor Red
}

exit $code