[CmdletBinding()]
param(
    [switch]$SkipBlockG,     # allow bypass only if you explicitly ask for it
    [switch]$ProducersOnly   # run producer diagnostics only; never arms orders
)

$ErrorActionPreference = 'Stop'

# Script lives under repoRoot\tools
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$checker   = Join-Path $repoRoot 'tools\Check-BlockGReady.ps1'
$oneTap    = Join-Path $repoRoot 'tools\PreMarket-OneTap.ps1'
$phase3Runner = Join-Path $repoRoot "tools\Run-Phase3GateScoreDaily.ps1"
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



if ($ProducersOnly) {
    Write-Host "[NVDA-PREMKT] ProducersOnly: running safety+Phase3 producers WITHOUT Block-G arming." -ForegroundColor Cyan

    # --- EV-HARD computed input + daily export (fail-closed, no manual ok) ---
        $evSnap = Join-Path $repoRoot "tools\Build-EvHardSnapshot.ps1"
    if (Test-Path $evSnap) {
        Write-Host "[NVDA-PREMKT] ProducersOnly: building EV-hard snapshot (today) ..." -ForegroundColor Cyan
        & $evSnap
        Write-Host "[NVDA-PREMKT] ProducersOnly: ev_hard_snapshot_exit=$LASTEXITCODE" -ForegroundColor DarkCyan
    } else {
        Write-Host "[NVDA-PREMKT] ProducersOnly: WARN EV-hard snapshot builder not found; skipping." -ForegroundColor Yellow
    }
$evCompute = Join-Path $repoRoot "tools\Compute-Phase5EvHardSnapshotInput.ps1"
    if (Test-Path $evCompute) {
        Write-Host "[NVDA-PREMKT] ProducersOnly: computing EV-hard snapshot input ..." -ForegroundColor Cyan
        & $evCompute -EvidencePath ".\logs\ev_hard_snapshot.json"
        Write-Host "[NVDA-PREMKT] ProducersOnly: ev_hard_compute_exit=$LASTEXITCODE" -ForegroundColor DarkCyan
    } else {
        Write-Host "[NVDA-PREMKT] ProducersOnly: WARN EV-hard compute tool not found; skipping." -ForegroundColor Yellow
    }

    $evExport = Join-Path $repoRoot "tools\Export-Phase5EvHardVetoDailySnapshot.ps1"
    if (Test-Path $evExport) {
        Write-Host "[NVDA-PREMKT] ProducersOnly: exporting EV-hard daily snapshot ..." -ForegroundColor Cyan
        & $evExport
        Write-Host "[NVDA-PREMKT] ProducersOnly: ev_hard_export_exit=$LASTEXITCODE" -ForegroundColor DarkCyan
    } else {
        Write-Host "[NVDA-PREMKT] ProducersOnly: WARN EV-hard export tool not found; skipping." -ForegroundColor Yellow
    }
    # Phase-5 Safety Snapshot (optional)
    $phase5SafetyRunner = Join-Path $repoRoot "tools\Run-Phase5SafetySnapshot.ps1"
    if (Test-Path $phase5SafetyRunner) {
        Write-Host "[NVDA-PREMKT] ProducersOnly: Running Run-Phase5SafetySnapshot.ps1 ..." -ForegroundColor Cyan
        & $phase5SafetyRunner
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[NVDA-PREMKT] ProducersOnly: Phase-5 safety snapshot failed. exitCode=$LASTEXITCODE" -ForegroundColor Red
            exit $LASTEXITCODE
        }
    } else {
        Write-Host "[NVDA-PREMKT] ProducersOnly: WARN Run-Phase5SafetySnapshot.ps1 not found; skipping." -ForegroundColor Yellow
    }

    # Phase-3 GateScore Daily build (writes gatescore_daily_build.jsonl)
    if (-not (Test-Path $phase3Runner)) {
        Write-Host "[NVDA-PREMKT] ProducersOnly: ERROR Run-Phase3GateScoreDaily.ps1 not found at $phase3Runner" -ForegroundColor Red
        exit 1
    }

    Write-Host "[NVDA-PREMKT] ProducersOnly: Running Run-Phase3GateScoreDaily.ps1 -Symbol NVDA ..." -ForegroundColor Cyan
    & $phase3Runner -Symbol "NVDA" -StatusPath ".\logs\blockg_status_stub.json" -Out ".\logs\gatescore_daily_build.jsonl"
    $gsExit = $LASTEXITCODE

# In ProducersOnly, exitCode=2 is expected fail-closed ("not ready") ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â keep outputs and continue.
# Only non-(0,2) indicates a real script failure.
if ($gsExit -ne 0 -and $gsExit -ne 2) {
    Write-Host "[NVDA-PREMKT] ProducersOnly: ERROR Phase-3 GateScore daily build failed (exitCode=$gsExit)." -ForegroundColor Red
    exit $gsExit
}

if ($gsExit -eq 2) {
    Write-Host "[NVDA-PREMKT] ProducersOnly: Phase-3 GateScore not-ready (exitCode=2) -> recorded outputs; continuing." -ForegroundColor Yellow
}# Rebuild GateScore summaries (optional wrapper)
    $gsWrap = Join-Path $repoRoot "tools\Run-BuildGateScoreSummaries.ps1"
    if (Test-Path $gsWrap) {
        Write-Host "[NVDA-PREMKT] ProducersOnly: Rebuilding GateScore summaries ..." -ForegroundColor Cyan
        & $gsWrap
    } else {
        Write-Host "[NVDA-PREMKT] ProducersOnly: WARN Run-BuildGateScoreSummaries.ps1 not found; skipping." -ForegroundColor Yellow
    }

    Write-Host "[NVDA-PREMKT] ProducersOnly complete (no arming attempted)." -ForegroundColor Yellow
    exit 0
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
# ---- Phase-3 GateScore Daily (canonical one-tap) ----
if (-not (Test-Path $phase3Runner)) {
    Write-Host "[NVDA-PREMKT] ERROR: Run-Phase3GateScoreDaily.ps1 not found at $phase3Runner; refusing to continue." -ForegroundColor Red
    exit 1
}

Write-Host "[NVDA-PREMKT] Running Run-Phase3GateScoreDaily.ps1 -Symbol NVDA ..." -ForegroundColor Cyan
& $phase3Runner -Symbol "NVDA" -StatusPath ".\logs\blockg_status_stub.json" -Out ".\logs\gatescore_daily_build.jsonl"
$gsExit = $LASTEXITCODE

if ($gsExit -ne 0) {
    Write-Host "[NVDA-PREMKT] ERROR: Phase-3 GateScore daily build failed (exitCode=$gsExit). Aborting NVDA pre-market one-tap." -ForegroundColor Red
    exit $gsExit
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