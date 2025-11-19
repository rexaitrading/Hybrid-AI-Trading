[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# Resolve repo root from this script's folder (tools -> repo root)
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo

Write-Host ""
Write-Host "===== PreMarket-Phase5: Running core PreMarket-Check.ps1 =====" -ForegroundColor Cyan
Write-Host ""

# Run the standard pre-market gate (RiskPulse + QoS)
$preMarketScript = Join-Path $PSScriptRoot "PreMarket-Check.ps1"
if (-not (Test-Path $preMarketScript)) {
    Write-Host "[PHASE5-WRAPPER] ERROR: PreMarket-Check.ps1 not found at $preMarketScript" -ForegroundColor Red
    exit 1
}

& $preMarketScript
$preCode = $LASTEXITCODE

Write-Host ""
Write-Host ("[PHASE5-WRAPPER] PreMarket-Check.ps1 exit code: {0}" -f $preCode) -ForegroundColor Yellow
Write-Host ""

# Always show the AAPL Phase 5 promotion checklist after the core decision
Write-Host "===== Phase 5 (AAPL) Promotion Checklist =====" -ForegroundColor Cyan
Write-Host ""

$checklistScript = Join-Path $PSScriptRoot "Show-Phase5AaplPromotionChecklist.ps1"
if (Test-Path $checklistScript) {
    . $checklistScript
}
else {
    Write-Host "[PHASE5-WRAPPER] Checklist script not found at $checklistScript (skipping)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host ("[PHASE5-WRAPPER] Done. Final PreMarket-Check exit code: {0}" -f $preCode) -ForegroundColor Yellow

exit $preCode