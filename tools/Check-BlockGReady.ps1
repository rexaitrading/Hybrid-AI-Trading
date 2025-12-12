[CmdletBinding()]
param(
    [Parameter()]
    [string]$Symbol = "NVDA",

    # GateScore policy (TEMP defaults; tighten later)
    [double]$GateScoreMin = 0.0,
    [int]$GateScoreMinSamples = 3
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Set-LastExitCode {
    param([int]$Code)
    $global:LASTEXITCODE = $Code
    return
}

$toolsDir     = Split-Path -Parent $PSCommandPath
$repoRoot     = Split-Path -Parent $toolsDir
$logsPath     = Join-Path $repoRoot "logs"
$contractPath = Join-Path $logsPath "blockg_status_stub.json"
$gateScoreCsv = Join-Path $logsPath "gatescore_daily_summary.csv"

$symUpper = $Symbol.ToUpper()
$today    = (Get-Date).ToString("yyyy-MM-dd")

Write-Host "[BLOCK-G] Check-BlockGReady.ps1 -Symbol $symUpper" -ForegroundColor Cyan
Write-Host "[BLOCK-G] Today = $today" -ForegroundColor DarkGray
Write-Host "[BLOCK-G] Contract path: $contractPath" -ForegroundColor DarkGray
Write-Host "[BLOCK-G] GateScore CSV: $gateScoreCsv" -ForegroundColor DarkGray

# ---- GateScore checks (fail-closed, return-only) ----
if (-not (Test-Path $gateScoreCsv)) {
    Write-Host "[BLOCK-G] ERROR: gatescore_daily_summary.csv missing." -ForegroundColor Red
    Set-LastExitCode 3; return
}

$rows = $null
try { $rows = Import-Csv $gateScoreCsv } catch { $rows = $null }

if (-not $rows) {
    Write-Host "[BLOCK-G] ERROR: failed to read gatescore_daily_summary.csv" -ForegroundColor Red
    Set-LastExitCode 3; return
}

$row = $rows | Where-Object { $_.symbol -eq $symUpper } | Select-Object -Last 1
if (-not $row) {
    Write-Host "[BLOCK-G] ERROR: no GateScore row for $symUpper" -ForegroundColor Red
    Set-LastExitCode 3; return
}

if ([string]$row.as_of_date -ne $today) {
    Write-Host "[BLOCK-G] ERROR: GateScore stale (as_of_date=$($row.as_of_date), today=$today)" -ForegroundColor Red
    Set-LastExitCode 3; return
}

$score = 0.0
$samples = 0
try { $score = [double]$row.mean_edge_ratio } catch { $score = 0.0 }
try { $samples = [int]$row.pnl_samples } catch { $samples = 0 }

if ($samples -lt $GateScoreMinSamples) {
    Write-Host "[BLOCK-G] GateScore FAIL: pnl_samples=$samples < $GateScoreMinSamples" -ForegroundColor Yellow
    Set-LastExitCode 1; return
}

if ($score -lt $GateScoreMin) {
    Write-Host "[BLOCK-G] GateScore FAIL: mean_edge_ratio=$score < $GateScoreMin" -ForegroundColor Yellow
    Set-LastExitCode 1; return
}

Write-Host "[BLOCK-G] GateScore OK (samples=$samples score=$score)" -ForegroundColor Green

# ---- Contract checks ----
if (-not (Test-Path $contractPath)) {
    Write-Host "[BLOCK-G] ERROR: Contract JSON not found." -ForegroundColor Red
    Set-LastExitCode 1; return
}

try {
    $status = Get-Content $contractPath -Raw | ConvertFrom-Json
} catch {
    Write-Host "[BLOCK-G] ERROR: Failed to parse contract JSON." -ForegroundColor Red
    Set-LastExitCode 1; return
}

if (-not ($status.PSObject.Properties.Name -contains "as_of_date")) {
    Write-Host "[BLOCK-G] ERROR: Contract missing as_of_date." -ForegroundColor Red
    Set-LastExitCode 3; return
}

if ([string]$status.as_of_date -ne $today) {
    Write-Host "[BLOCK-G] ERROR: Contract stale (as_of_date=$($status.as_of_date), today=$today)" -ForegroundColor Red
    Set-LastExitCode 3; return
}

$symbolKey = ($symUpper.ToLower() + "_blockg_ready")
if (-not ($status.PSObject.Properties.Name -contains $symbolKey)) {
    Write-Host "[BLOCK-G] ERROR: Contract missing field: $symbolKey" -ForegroundColor Red
    Set-LastExitCode 3; return
}

$ready = [bool]($status.$symbolKey)

if ($ready) {
    Write-Host "[BLOCK-G] $symUpper Block-G READY (contract $symbolKey=True)." -ForegroundColor Green
    Set-LastExitCode 0; return
}

Write-Host "[BLOCK-G] $symUpper Block-G NOT READY (contract $symbolKey=False)." -ForegroundColor Yellow
Set-LastExitCode 1; return
