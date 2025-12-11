[CmdletBinding()]
param(
    [switch]$SkipBlockG  # allow bypass only if you explicitly ask for it
)

$ErrorActionPreference = 'Stop'

# Script lives under repoRoot\tools
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$checker   = Join-Path $repoRoot 'tools\Check-BlockGReady.ps1'
$oneTap    = Join-Path $repoRoot 'tools\PreMarket-OneTap.ps1'

Write-Host "[NVDA-PREMKT] PreMarket-OneTap *gated* wrapper (NVDA Block-G contract)" -ForegroundColor Cyan

if (-not (Test-Path $oneTap)) {
    Write-Host "[NVDA-PREMKT] ERROR: PreMarket-OneTap.ps1 not found at $oneTap" -ForegroundColor Red
    exit 1
}

# Optional debug path: bypass Block-G only if explicitly requested
if ($SkipBlockG) {
    Write-Host "[NVDA-PREMKT] WARNING: -SkipBlockG specified -> BYPASSING NVDA Block-G contract check." -ForegroundColor Yellow
    Write-Host "[NVDA-PREMKT] Calling PreMarket-OneTap.ps1 directly (for debugging only)." -ForegroundColor Yellow
    & $oneTap
    exit $LASTEXITCODE
}

# ---- Phase-5 Safety Snapshot (RunContext + Block-G + CSV + dashboard) ----
$phase5SafetyRunner = Join-Path $repoRoot "tools\Run-Phase5SafetySnapshot.ps1"
if (-not (Test-Path $phase5SafetyRunner)) {
    Write-Host "[NVDA-PREMKT] WARN: Run-Phase5SafetySnapshot.ps1 not found; skipping full safety snapshot." -ForegroundColor Yellow
} else {
    Write-Host "[NVDA-PREMKT] Running Run-Phase5SafetySnapshot.ps1 (Phase-5 safety stack)..." -ForegroundColor Cyan
    & $phase5SafetyRunner
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[NVDA-PREMKT] ERROR: Phase-5 safety snapshot failed. Aborting NVDA pre-market one-tap." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# Normal path: enforce Block-G contract before arming anything NVDA-related
if (-not (Test-Path $checker)) {
    Write-Host "[NVDA-PREMKT] ERROR: Check-BlockGReady.ps1 not found at $checker; refusing to continue." -ForegroundColor Red
    exit 1
}

Write-Host "[NVDA-PREMKT] Running Check-BlockGReady.ps1 -Symbol NVDA..." -ForegroundColor Cyan
& $checker -Symbol NVDA
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "[NVDA-PREMKT] NVDA Block-G READY = False (contract exitCode=$exitCode)" -ForegroundColor Yellow
    Write-Host "[NVDA-PREMKT] REFUSING to run PreMarket-OneTap.ps1 for NVDA live/paper arming." -ForegroundColor Yellow
    exit 2
}

Write-Host "[NVDA-PREMKT] NVDA Block-G READY = True (contract satisfied; diagnostics chain green)" -ForegroundColor Green
Write-Host "[NVDA-PREMKT] Calling PreMarket-OneTap.ps1 (usual pre-market flow)" -ForegroundColor Cyan

& $oneTap
$oneTapExit = $LASTEXITCODE
Write-Host "[NVDA-PREMKT] PreMarket-OneTap.ps1 exit code = $oneTapExit" -ForegroundColor Cyan
exit $oneTapExit