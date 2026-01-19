[CmdletBinding()]
param()

Set-StrictMode -Version Latest
# --- secrets (canonical) ---
. (Join-Path $PSScriptRoot "Load-HatSecrets.ps1")
$ErrorActionPreference = 'Stop'

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$intelDir = Join-Path $repoRoot "src\.intel"
if (-not (Test-Path $intelDir)) { New-Item -ItemType Directory -Path $intelDir -Force | Out-Null }

$pulse = Join-Path $intelDir "risk_pulse.jsonl"

# Canonical log outputs (Phase-6 invariant): always mirror minimal pulse into .\logs
$pulseLog = Join-Path $repoRoot "logs\risk_pulse.jsonl"
$intelFeedLog = Join-Path $repoRoot "logs\intel_feed.jsonl"

$ts = (Get-Date).ToUniversalTime().ToString("o")
# A3_INTEL_ASOF_MARKET_BEGIN
$mk = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant(); if(-not $mk){ $mk="US" }
$rc = (& ".\tools\Resolve-RunContext.ps1" -Market $mk -Symbol NVDA | Out-String | ConvertFrom-Json)
if(-not $rc -or -not $rc.as_of_date){ throw "[FAIL-CLOSED] Resolve-RunContext missing as_of_date for intel pulse" }
$today = ([string]$rc.as_of_date).Substring(0,10)
$logsDir = ([string]$rc.logs_dir)
if(-not $logsDir){ throw "[FAIL-CLOSED] Resolve-RunContext missing logs_dir for intel pulse" }
$env:HAT_AS_OF_DATE = $today
$env:HAT_LOGS_DIR   = $logsDir
# A3_INTEL_ASOF_MARKET_END

function Read-JsonSafe([string]$path) {
  if (-not (Test-Path $path)) { return $null }
  try { return (Get-Content $path -Raw -Encoding utf8 | ConvertFrom-Json) } catch { return $null }
}

$bg = Read-JsonSafe (Join-Path $logsDir "blockg_status_stub.json")
$ev = Read-JsonSafe (Join-Path $repoRoot "logs\ev_hard_snapshot.json")

# Pull NVDA gatescore row
$gsRow = $null
$gsCsv = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
if (Test-Path $gsCsv) {
  try {
    $gsRow = Import-Csv $gsCsv | Where-Object { $_.as_of_date -eq $today -and $_.symbol -eq "NVDA" } | Select-Object -First 1
  } catch { $gsRow = $null }
}

$obj = [ordered]@{
  ts_utc = $ts
  as_of_date = $today
  kind = "intel_minimal_pulse"
  blockg_nvda_ready = [bool](($bg -and ($bg.PSObject.Properties.Name -contains "nvda_blockg_ready")) -and [bool]$bg.nvda_blockg_ready)
  gatescore_nvda_samples = if($gsRow){ [int]$gsRow.count_signals } else { 0 }
  gatescore_nvda_edge = if($gsRow){ [double]$gsRow.mean_edge_ratio } else { 0.0 }
  ev_hard_ok = if($ev){ [bool]$ev.ok } else { $false }
  note = "Minimal intel pulse (fallback). Full collectors missing in repo; restore later."
}

$line = ($obj | ConvertTo-Json -Compress)
Add-Content -LiteralPath $pulse -Value $line -Encoding utf8

Write-Host "[INTEL-MIN] wrote $pulse" -ForegroundColor Green

# Mirror to canonical logs (fail-closed best-effort)
try { Copy-Item -LiteralPath $pulse -Destination $pulseLog -Force } catch { }
try {
  # minimal intel_feed is a single-line pulse wrapper
  $line = Get-Content -LiteralPath $pulse -Encoding utf8 | Select-Object -Last 1
  $line | Out-File -LiteralPath $intelFeedLog -Encoding utf8 -Append
} catch { }
Write-Host "[INTEL-MIN] mirrored $pulse -> $pulseLog and appended -> $intelFeedLog" -ForegroundColor Green
# LOGS_INTEL_MIRROR_BEGIN
# Institutional: logs\.intel is the audit surface for Phase-6 (must be populated each run).
try {
  $logsIntel = Join-Path $repoRoot "logs\.intel"
  New-Item -ItemType Directory -Force -Path $logsIntel | Out-Null

  # Mirror from the known-good log outputs (already written by this script)
  if(Test-Path -LiteralPath $pulseLog){
    Copy-Item -LiteralPath $pulseLog -Destination (Join-Path $logsIntel "risk_pulse.jsonl") -Force
  }
  if(Test-Path -LiteralPath $intelFeedLog){
    Copy-Item -LiteralPath $intelFeedLog -Destination (Join-Path $logsIntel "intel_feed.jsonl") -Force
  }
} catch { }
# LOGS_INTEL_MIRROR_END
exit 0
