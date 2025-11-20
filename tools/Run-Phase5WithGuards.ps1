[CmdletBinding()]
param(
    [string]$DateTag = (Get-Date -Format 'yyyyMMdd')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptRoot = $PSScriptRoot
$repoRoot   = Split-Path -Parent $scriptRoot
Set-Location $repoRoot

$preflight  = Join-Path $repoRoot 'tools\Preflight-Phase5Guard.ps1'
$exportRisk = Join-Path $repoRoot 'tools\Export-Phase5RiskEnv.ps1'
$runPhase5  = Join-Path $repoRoot 'tools\Run-Phase5MultiStrategy.ps1'

if (-not (Test-Path $preflight)) {
    throw "Missing preflight guard script: $preflight"
}
if (-not (Test-Path $exportRisk)) {
    throw "Missing Phase5 risk env exporter: $exportRisk"
}
if (-not (Test-Path $runPhase5)) {
    throw "Missing Phase5 multi-strategy runner: $runPhase5"
}

Write-Host "=== Phase5 Orchestrator (Preflight + Risk + Engine) ===" -ForegroundColor Cyan
Write-Host "Repo    : $repoRoot"
Write-Host "DateTag : $DateTag"
Write-Host ""

# 1) Preflight: session calendar / allowed trading window
Write-Host "[STEP 1] Running Preflight-Phase5Guard.ps1..." -ForegroundColor Cyan
& $preflight -DateTag $DateTag
$preflightExit = $LASTEXITCODE

if ($preflightExit -ne 0) {
    Write-Host "[PHASE5-ORCH] Preflight FAILED (exit=$preflightExit). Aborting Phase5 run." -ForegroundColor Yellow
    exit $preflightExit
}
Write-Host "[PHASE5-ORCH] Preflight OK; session open and calendar allowed." -ForegroundColor Green
Write-Host ""

# 2) Load Phase5 risk config into environment
Write-Host "[STEP 2] Loading Phase5 risk env from config\phase5_risk.json..." -ForegroundColor Cyan
& $exportRisk
$riskExit = $LASTEXITCODE

if ($riskExit -ne 0) {
    Write-Host "[PHASE5-ORCH] Export-Phase5RiskEnv FAILED (exit=$riskExit). Aborting Phase5 run." -ForegroundColor Yellow
    exit $riskExit
}
Write-Host "[PHASE5-ORCH] Risk env loaded (daily loss cap, MDD, cooldown, no-averaging, allowed strategies)." -ForegroundColor Green
Write-Host ""

# 3) Run the Phase5 multi-strategy runner (NVDA B+, SPY/QQQ ORB, etc.)
Write-Host "[STEP 3] Running Run-Phase5MultiStrategy.ps1..." -ForegroundColor Cyan
& $runPhase5 -DateTag $DateTag
$engineExit = $LASTEXITCODE

Write-Host "[PHASE5-ORCH] Run-Phase5MultiStrategy.ps1 exit code = $engineExit" -ForegroundColor Cyan
exit $engineExit