param(
    [Parameter(Mandatory = $false)][string] $Symbol,
    [Parameter(Mandatory = $false)][string] $Session,
    [Parameter(Mandatory = $false)][string] $SummaryJson = ""
)

$ErrorActionPreference = 'Stop'

# Determine repo root (supports both script + interactive)
if ($MyInvocation.MyCommand.Path) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $repoRoot  = Resolve-Path (Join-Path $scriptDir '..')
} else {
    $repoRoot = Get-Location
}

Set-Location $repoRoot

# --- Phase-5 microsuite gate (auto-added) ---
Write-Host "[ONETAP] Running Phase-5 microsuite..." -ForegroundColor Yellow
try {
    .\tools\Run-Phase5MicroSuite.ps1
} catch {
    Write-Host "[ONETAP] Phase-5 microsuite threw an exception:" -ForegroundColor Red
    Write-Host $_ -ForegroundColor Red
    exit 1
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ONETAP] Phase-5 microsuite FAILED, aborting PreMarket-OneTap." -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "[ONETAP] Phase-5 microsuite PASSED, continuing PreMarket-OneTap..." -ForegroundColor Green
# --- End Phase-5 microsuite gate ---


# --- Phase-5 EV sync gate ---------------------------------------------
# Require a successful Run-Phase5EvSync.ps1 before launching IB paper/live.
try {
    $evStatusPath = Join-Path $repoRoot 'logs\phase5_ev_sync_status.json'
    if (-not (Test-Path $evStatusPath)) {
        Write-Host "[PHASE5-EV] ERROR: phase5_ev_sync_status.json not found. Run Run-Phase5EvSync.ps1 first." -ForegroundColor Red
        return
    }

    $evStatusJson = Get-Content $evStatusPath -Raw
    $evStatus     = $evStatusJson | ConvertFrom-Json

    if (-not $evStatus.success) {
        Write-Host "[PHASE5-EV] ERROR: Last Phase-5 EV sync did not succeed (success=false). Fix EV sync before trading." -ForegroundColor Red
        return
    }

    Write-Host "[PHASE5-EV] EV sync check passed (phase5_ev_sync_status.json success=true)." -ForegroundColor Green
}
catch {
    Write-Host ("[PHASE5-EV] ERROR checking EV sync status: {0}" -f $_.Exception.Message) -ForegroundColor Red
    return
}
# -----------------------------------------------------------------------

# --- Phase-5 EV hard veto daily snapshot (Notion wiring) ---
.\tools\Invoke-Phase5EvHardVetoDaily.ps1
# -----------------------------------------------------------


Write-Host "[ONETAP] PreMarket-OneTap complete (exit 0)" -ForegroundColor Green
exit 0

# Phase-5 EV hard-veto configuration summary
Write-Host "`n[EV-HARD] Phase-5 EV hard-veto summary (SPY/QQQ):" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'Build-EvHardVetoSummary.ps1')