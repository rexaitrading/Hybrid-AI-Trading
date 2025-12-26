[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$intelDir = Join-Path $repoRoot "src\.intel"
if (-not (Test-Path $intelDir)) { New-Item -ItemType Directory -Path $intelDir -Force | Out-Null }

$pulse = Join-Path $intelDir "risk_pulse.jsonl"
$ts = (Get-Date).ToUniversalTime().ToString("o")
$today = (Get-Date).ToString("yyyy-MM-dd")

function Read-JsonSafe([string]$path) {
  if (-not (Test-Path $path)) { return $null }
  try { return (Get-Content $path -Raw -Encoding utf8 | ConvertFrom-Json) } catch { return $null }
}

$bg = Read-JsonSafe (Join-Path $repoRoot "logs\blockg_status_stub.json")
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
  blockg_nvda_ready = [bool]($bg.nvda_blockg_ready)
  gatescore_nvda_samples = if($gsRow){ [int]$gsRow.count_signals } else { 0 }
  gatescore_nvda_edge = if($gsRow){ [double]$gsRow.mean_edge_ratio } else { 0.0 }
  ev_hard_ok = if($ev){ [bool]$ev.ok } else { $false }
  note = "Minimal intel pulse (fallback). Full collectors missing in repo; restore later."
}

$line = ($obj | ConvertTo-Json -Compress)
Add-Content -LiteralPath $pulse -Value $line -Encoding utf8

Write-Host "[INTEL-MIN] wrote $pulse" -ForegroundColor Green
exit 0