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

exit $code

# === Phase5 Notion journal day creation =====================================
# This section creates (idempotent) Phase 5 LIVE ORB/VWAP Trading Journal rows
# for AAPL, SPY, and QQQ using the New-Phase5Day*.ps1 helpers.
# Idempotency is handled via intel\notion_flags\phase5_{SYMBOL}_YYYYMMDD.flag
# so calling this block multiple times per day is safe.
try {
    Write-Host "[PreMarket-Check] Phase5: creating Notion journal rows for AAPL/SPY/QQQ (idempotent)" -ForegroundColor Cyan

    $phase5Scripts = @(
        'tools\New-Phase5Day.ps1',       # AAPL
        'tools\New-Phase5Day-SPY.ps1',   # SPY
        'tools\New-Phase5Day-QQQ.ps1'    # QQQ
    )

    foreach ($s in $phase5Scripts) {
        if (Test-Path $s) {
            Write-Host "[PreMarket-Check] Invoking $s" -ForegroundColor DarkCyan
            & $s
        } else {
            Write-Host "[PreMarket-Check] WARNING: Missing Phase5 day script $s; skipping." -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "[PreMarket-Check] WARNING: Phase5 Notion day creation failed: $($_.Exception.Message)" -ForegroundColor Yellow
}
# === End Phase5 Notion journal day creation =================================
# === Optional NVDA Phase-5 live-style smoke (no broker side effects) ===
if ($env:HAT_ENABLE_NVDA_PHASE5_LIVE -eq '1') {
    Write-Host "[Phase5] Running nvda_phase5_live_runner (dry_run)" -ForegroundColor Cyan
    try {
        .\.venv\Scripts\python.exe -m hybrid_ai_trading.runners.nvda_phase5_live_runner
    } catch {
        Write-Warning "[Phase5] nvda_phase5_live_runner failed: $($_.Exception.Message)"
    }
} else {
    Write-Host "[Phase5] NVDA Phase-5 live runner disabled (HAT_ENABLE_NVDA_PHASE5_LIVE not set to '1')." `
        -ForegroundColor DarkGray
}
# -----------------------------------------------------------------------------
# Phase-5 NVDA live sanity / no-averaging-down demo (optional, manual):
#
# To run NVDA Phase-5 live-style smoke (dry_run) together with the double-BUY
# demo from your pre-market pipeline, use:
#
#   PS> \ = '1'
#   PS> \ = '1'
#   PS> .\tools\PreMarket-Check.ps1
#   PS> Remove-Item Env:HAT_ENABLE_NVDA_PHASE5_LIVE      -ErrorAction SilentlyContinue
#   PS> Remove-Item Env:HAT_PHASE5_DOUBLE_BUY_DEMO       -ErrorAction SilentlyContinue
#
# This will:
#   - Run nvda_phase5_live_runner in dry_run mode (no broker side effects),
#   - Send a first NVDA_BPLUS_LIVE BUY (paper fill),
#   - Attempt a second BUY in the same process under Phase-5 demo wiring
#     (currently fills; future work will wire real position state so the
#      Phase-5 no-averaging helper can reject the second order).
#
# Default scheduled pre-market runs remain unchanged unless these env vars
# are explicitly set.
# -----------------------------------------------------------------------------
