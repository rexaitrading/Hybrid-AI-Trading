# --- Phase-5 microsuite gate (auto-added) ---
Write-Host "[PREMARKET] Running Phase-5 microsuite..." -ForegroundColor Yellow
try {
    .\tools\Run-Phase5MicroSuite.ps1
} catch {
    Write-Host "[PREMARKET] Phase-5 microsuite threw an exception:" -ForegroundColor Red
    Write-Host $_ -ForegroundColor Red
    exit 1
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "[PREMARKET] Phase-5 microsuite FAILED, aborting PreMarket-Check." -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "[PREMARKET] Phase-5 microsuite PASSED, continuing PreMarket-Check..." -ForegroundColor Green
# --- End Phase-5 microsuite gate ---
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Derive repo root from this script's folder (tools -> repo root)
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo

# STEP 0: Phase-5 EV + Risk preflight (optional but recommended)
$toolsDir   = Join-Path $repo 'tools'
$evPreflight = Join-Path $toolsDir "Run-Phase5EvPreflight.ps1"
if (Test-Path $evPreflight) {
    Write-Host "`n[STEP 0] Phase-5 EV + Risk Preflight" -ForegroundColor Yellow
    & $evPreflight
} else {
    Write-Host "[STEP 0] Skipping Phase-5 EV preflight (Run-Phase5EvPreflight.ps1 not found at $evPreflight)" -ForegroundColor DarkYellow
}

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

# --- RouteErrors risk summary (from logs\paper_route_errors.jsonl, last 24h) ---
try {
    $routeLogPath  = Join-Path $repo 'logs\paper_route_errors.jsonl'
    $lookbackHours = 24
    $cutoff        = (Get-Date).ToUniversalTime().AddHours(-$lookbackHours)

    if (-not (Test-Path $routeLogPath)) {
        Write-Host "[Route] OK - no paper_route_errors.jsonl found; 0 route_fail event(s) in last $lookbackHours hour(s)." -ForegroundColor Green
    } else {
        $lines = Get-Content $routeLogPath -ErrorAction SilentlyContinue | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

        if (-not $lines -or $lines.Count -eq 0) {
            Write-Host "[Route] OK - paper_route_errors.jsonl is empty; 0 route_fail event(s) in last $lookbackHours hour(s)." -ForegroundColor Green
        } else {
            $records = @()
            foreach ($line in $lines) {
                try {
                    $rec = $line | ConvertFrom-Json -ErrorAction Stop
                    $records += $rec
                } catch {
                    Write-Host "[Route] WARN - skipping invalid JSON line in paper_route_errors.jsonl" -ForegroundColor Yellow
                }
            }

            if (-not $records -or $records.Count -eq 0) {
                Write-Host "[Route] OK - no valid route_fail records; 0 event(s) in last $lookbackHours hour(s)." -ForegroundColor Green
            } else {
                $recent = $records | Where-Object {
                    $_.ts_logged -and ([DateTime]::Parse($_.ts_logged) -ge $cutoff)
                }

                $countRecent = ($recent | Measure-Object).Count

                if ($countRecent -gt 0) {
                    $routeFlag  = "CAUTION"
                    $routeColor = "Yellow"
                } else {
                    $routeFlag  = "OK"
                    $routeColor = "Green"
                }

                Write-Host ("[Route] {0} - {1} route_fail event(s) in last {2} hour(s)." -f $routeFlag, $countRecent, $lookbackHours) -ForegroundColor $routeColor
            }
        }
    }
} catch {
    Write-Host ("[Route] WARN - unable to summarize route errors: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
}
# -----------------------------------------------------------------------------


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

# --- Phase-5 Option A sanity hook (SPY / QQQ / NVDA) ---
try {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $sanityPath = Join-Path $scriptRoot "Phase5-OptionA-Sanity.ps1"

    if (Test-Path $sanityPath) {
        Write-Host "" 
        Write-Host "[PHASE-5] Running Option A ORB multi-symbol sanity..." -ForegroundColor Cyan
        & $sanityPath
    } else {
        Write-Host "[PHASE-5] Skipping Option A sanity (Phase5-OptionA-Sanity.ps1 not found)." -ForegroundColor DarkYellow
    }
} catch {
    Write-Host "[PHASE-5] Option A sanity threw an error: $($_.Exception.Message)" -ForegroundColor Red
}
# --- End Phase-5 Option A sanity hook ---

# === Phase-5: microsuite pre-flight checks ===================================
Write-Host ""
Write-Host "[PREMARKET] Phase-5 microsuites (risk + portfolio/exec)" -ForegroundColor Cyan

try {
    Write-Host "[PREMARKET] Running Phase-5 risk microsuite..." -ForegroundColor Cyan
    .\tools\Run-Phase5Tests.ps1
    Write-Host "[PREMARKET] Phase-5 risk microsuite: OK" -ForegroundColor Green
}
catch {
    Write-Host "[PREMARKET] Phase-5 risk microsuite: FAILED" -ForegroundColor Red
    throw
}

try {
    Write-Host "[PREMARKET] Running portfolio/exec microsuite..." -ForegroundColor Cyan
    .\tools\Run-PortfolioExecTests.ps1
    Write-Host "[PREMARKET] Portfolio/exec microsuite: OK" -ForegroundColor Green
}
catch {
    Write-Host "[PREMARKET] Portfolio/exec microsuite: FAILED" -ForegroundColor Red
    throw
}
# ============================================================================
Write-Host "`n[PHASE5 CHECK] NVDA Phase-5 IB paper connectivity (dry run via live runner)" -ForegroundColor Cyan

$env:HAT_IB_HOST    = "127.0.0.1"
$env:HAT_IB_PORT    = "7497"
$env:HAT_IB_CLIENT_ID = "42"
$env:HAT_IB_ACCOUNT = "DUXXXXXXXX"
$env:HAT_PHASE5_ACCOUNT_DAILY_LOSS_CAP = "50"

# Here you might later add a special "check only" mode; for now it runs one small trade.
& .\.venv\Scripts\python.exe .\src\hybrid_ai_trading\runners\nvda_phase5_live_runner.py

# Phase-5 EV hard-veto configuration summary
Write-Host "`n[EV-HARD] Phase-5 EV hard-veto summary (SPY/QQQ):" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'Build-EvHardVetoSummary.ps1')