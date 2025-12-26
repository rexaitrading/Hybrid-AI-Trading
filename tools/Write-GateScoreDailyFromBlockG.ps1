[CmdletBinding()]
param(
  [string]$StatusPath = ".\logs\blockg_status_stub.json",
  [string]$DailyCsv   = ".\logs\gatescore_daily_summary_nvda.csv",
  [string]$SamplesCsv = ".\logs\nvda_gatescore_samples.csv",
  [string]$Symbol     = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $StatusPath)) { throw "Missing BlockG status: $StatusPath" }

$today = (Get-Date).ToString("yyyy-MM-dd")
$st = Get-Content -LiteralPath $StatusPath -Raw -Encoding utf8 | ConvertFrom-Json

if (-not $st.as_of_date) { throw "BlockG missing as_of_date" }
if ($st.as_of_date -ne $today) { throw "BlockG not fresh: as_of_date=$($st.as_of_date) need=$today" }

# Required GateScore fields (fail-closed)
$req = @(
  "gatescore_samples",
  "gatescore_pnl_samples",
  "gatescore_mean_edge_ratio",
  "gatescore_mean_micro_score"
)
foreach ($k in $req) {
  if (-not ($st.PSObject.Properties.Name -contains $k)) { throw "BlockG missing field: $k" }
}

$src = "REAL"
$countSignals = [int]$st.gatescore_samples
$pnlSamples   = [int]$st.gatescore_pnl_samples
$meanEdge     = [double]$st.gatescore_mean_edge_ratio
$meanMicro    = [double]$st.gatescore_mean_micro_score

# Write daily summary (overwrite with header + today row)
$dailyHeader = "as_of_date,symbol,source,count_signals,pnl_samples,mean_edge_ratio,mean_micro_score`n"
$dailyRow    = "{0},{1},{2},{3},{4},{5},{6}`n" -f $today, $Symbol.ToUpperInvariant(), $src, $countSignals, $pnlSamples, $meanEdge, $meanMicro
[System.IO.File]::WriteAllText((Resolve-Path (Split-Path -Parent $DailyCsv) -ErrorAction SilentlyContinue).Path + "\" + (Split-Path -Leaf $DailyCsv), "", (New-Object System.Text.UTF8Encoding($false))) 2>$null | Out-Null

# ensure logs dir exists
$dailyDir = Split-Path -Parent $DailyCsv
if ($dailyDir -and -not (Test-Path $dailyDir)) { New-Item -ItemType Directory -Force -Path $dailyDir | Out-Null }

$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($DailyCsv, $dailyHeader + $dailyRow, $utf8)

# Upsert samples CSV (keep historical rows; ensure header; add today if missing)
$samplesDir = Split-Path -Parent $SamplesCsv
if ($samplesDir -and -not (Test-Path $samplesDir)) { New-Item -ItemType Directory -Force -Path $samplesDir | Out-Null }

if (-not (Test-Path -LiteralPath $SamplesCsv)) {
  $hdr = "as_of_date,score,count_signals,pnl_samples`n"
  [System.IO.File]::WriteAllText($SamplesCsv, $hdr, $utf8)
}

$lines = Get-Content -LiteralPath $SamplesCsv -Encoding utf8
$hasToday = $false
foreach ($ln in $lines) {
  if ($ln -match "^$today,") { $hasToday = $true; break }
}

if (-not $hasToday) {
  # define score as micro_score proxy (simple); you can replace later with true gatescore
  $score = [math]::Round($meanMicro, 6)
  $row = "{0},{1},{2},{3}`n" -f $today, $score, $countSignals, $pnlSamples
  [System.IO.File]::AppendAllText($SamplesCsv, $row, $utf8)
}

Write-Host "[PHASE3] Wrote daily summary: $DailyCsv" -ForegroundColor Green
Write-Host "[PHASE3] Upserted samples:    $SamplesCsv" -ForegroundColor Green
exit 0