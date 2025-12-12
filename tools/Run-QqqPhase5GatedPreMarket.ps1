[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

Set-Location $repoRoot

Write-Host "[QQQ-PREMKT] PreMarket *gated* wrapper (QQQ Block-G contract)" -ForegroundColor Cyan

# ---- Phase-5 RunContext stub (global safety view) ----
Write-Host "`n[RUNCTX] Phase-5 RunContext stub (SPY/QQQ view)" -ForegroundColor Yellow
$runCtxScript = Join-Path $toolsDir "Show-RunContextStub.ps1"
if (Test-Path $runCtxScript) {
    & $runCtxScript
} else {
    Write-Host "[RUNCTX] Show-RunContextStub.ps1 not found under tools\" -ForegroundColor DarkYellow
}

# ---- Phase-2 micro gate (SPY/QQQ) – shadow only for now ----
Write-Host "`n[PRECHECK] SPY/QQQ Phase-2 micro gate (shadow)" -ForegroundColor Yellow
$microPre = Join-Path $toolsDir "PreMarket-SpyQqqMicroGateCheck.ps1"
if (Test-Path $microPre) {
    & $microPre
} else {
    Write-Host "[PRECHECK] WARN: PreMarket-SpyQqqMicroGateCheck.ps1 not found; skipping micro gate precheck." -ForegroundColor DarkYellow
}

# ---- Phase-5 Safety Snapshot (RunContext + Block-G + CSV + dashboard) ----
$phase5SafetyRunner = Join-Path $repoRoot "tools\Run-Phase5SafetySnapshot.ps1"
if (-not (Test-Path $phase5SafetyRunner)) {
    Write-Host "[QQQ-PREMKT] WARN: Run-Phase5SafetySnapshot.ps1 not found; skipping full safety snapshot." -ForegroundColor Yellow
} else {
    Write-Host "[QQQ-PREMKT] Running Run-Phase5SafetySnapshot.ps1 (Phase-5 safety stack)..." -ForegroundColor Cyan
    & $phase5SafetyRunner
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[QQQ-PREMKT] ERROR: Phase-5 safety snapshot failed. Aborting QQQ Phase-5 gated pre-market." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# ---- Block-G contract check for QQQ ----
$checker = Join-Path $repoRoot "tools\Check-BlockGReady.ps1"
if (-not (Test-Path $checker)) {
    Write-Host "[QQQ-PREMKT] ERROR: Check-BlockGReady.ps1 not found at $checker; refusing to continue." -ForegroundColor Red
    exit 1
}

Write-Host "[QQQ-PREMKT] Running Check-BlockGReady.ps1 -Symbol QQQ..." -ForegroundColor Cyan
& $checker -Symbol QQQ
if ($LASTEXITCODE -ne 0) {
    Write-Host "[QQQ-PREMKT] QQQ Block-G NOT READY (exit $LASTEXITCODE). Aborting pre-market flow." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "[QQQ-PREMKT] QQQ Block-G READY = True (contract satisfied; diagnostics chain green)" -ForegroundColor Green

# ---- QQQ Phase-5 paper (or live) pipeline ----
$qqqPipeline = Join-Path $repoRoot "tools\Invoke-QqqPhase5PaperPipeline.ps1"
if (-not (Test-Path $qqqPipeline)) {
    Write-Host "[QQQ-PREMKT] WARNING: QQQ pipeline script not found at $qqqPipeline, nothing more to do." -ForegroundColor Yellow
    exit 0
}

Write-Host "[QQQ-PREMKT] Calling Invoke-QqqPhase5PaperPipeline.ps1..." -ForegroundColor Cyan
& $qqqPipeline
exit $LASTEXITCODE
