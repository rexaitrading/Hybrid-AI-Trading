$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Derive repo root from this script's folder (tools -> repo root)
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo

# Allow override via HAT_PYTHON; default to "python"
$py = $env:HAT_PYTHON
if (-not $py) {
    $py = "python"
}

# Run the Python pre-market gate (RiskPulse + QoS)
& $py -m hybrid_ai_trading.tools.pre_market_check
$code = $LASTEXITCODE

if ($code -eq 0) {
    Write-Host "Pre-market check: OK_TO_TRADE (exit 0)" -ForegroundColor Green
}
elseif ($code -eq 2) {
    Write-Host "Pre-market check: HALT (no RiskPulse snapshot; warm up replay/risk first)" -ForegroundColor Red
}
elseif ($code -eq 3) {
    Write-Host "Pre-market check: HALT (risk limits breached)" -ForegroundColor Red
}
elseif ($code -eq 4) {
    Write-Host "Pre-market check: HALT (provider QoS degraded)" -ForegroundColor Red
}
else {
    Write-Host ("Pre-market check: HALT (unexpected exit code {0})" -f $code) -ForegroundColor Red
}

exit $code# === Phase 5 AAPL Promotion Checklist (optional pre-flight) ===
try {
    Write-Host "" 
    Write-Host "==== Phase 5 (AAPL) Promotion Checklist (Lab  Tiny Live) ====" -ForegroundColor Cyan
    Write-Host ""

    $checklistScript = Join-Path $PSScriptRoot 'Show-Phase5AaplPromotionChecklist.ps1'
    if (Test-Path $checklistScript) {
        . $checklistScript
    }
    else {
        Write-Host "[PHASE5-AAPL-CHECKLIST] Checklist script not found at $checklistScript (skipping)." -ForegroundColor Yellow
    }
}
catch {
    Write-Host "[PHASE5-AAPL-CHECKLIST] Error while running Phase5 checklist: $_" -ForegroundColor Red
}
# === End Phase 5 AAPL Promotion Checklist block ===
