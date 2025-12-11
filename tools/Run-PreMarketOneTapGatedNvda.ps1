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

if ($SkipBlockG) {
    Write-Host "[NVDA-PREMKT] WARNING: -SkipBlockG specified -> BYPASSING NVDA Block-G contract check." -ForegroundColor Yellow
    Write-Host "[NVDA-PREMKT] Calling PreMarket-OneTap.ps1 directly (for debugging only)." -ForegroundColor Yellow
    & $oneTap
    exit $LASTEXITCODE
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