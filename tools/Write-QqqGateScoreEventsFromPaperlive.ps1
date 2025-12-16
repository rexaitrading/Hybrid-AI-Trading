[CmdletBinding()]
param(
  [ValidateSet("REAL")]
  [string]$Mode = "REAL"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logs  = Join-Path $repoRoot "logs"
$today = (Get-Date).ToString("yyyy-MM-dd")

$inJsonl  = Join-Path $logs "qqq_phase5_paperlive_results.jsonl"
$outJsonl = Join-Path $logs "qqq_gatescore_events.jsonl"

if (-not (Test-Path $inJsonl)) { throw "Missing input: $inJsonl" }

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outJsonl, "", $utf8NoBom)

function Get-EvProxy($obj) {
  if ($null -ne $obj.ev) {
    try { return [double]("$($obj.ev)") } catch { }
  }
  try {
    if ($null -ne $obj.phase5_result) {
      $d = $obj.phase5_result.phase5_details
      if ($null -eq $d) { $d = $obj.phase5_result.details }
      if ($null -ne $d -and $null -ne $d.ev_mu) {
        try { return [double]("$($d.ev_mu)") } catch { }
      }
    }
  } catch { }
  if ($null -ne $obj.ev_band_abs) {
    try { return -1.0 * [double]("$($obj.ev_band_abs)") } catch { }
  }
  return 0.0
}

function Get-MicroScore($obj) {
  # StrictMode-safe: do not touch missing properties directly
  try {
    if ($null -ne $obj -and $obj.PSObject -and ($obj.PSObject.Properties.Name -contains "micro_score")) {
      $v = $obj.PSObject.Properties["micro_score"].Value
      if ($null -ne $v) { return [double]("$v") }
    }
  } catch { }
  return 0.0
}

$rows = 0
Get-Content $inJsonl -Encoding utf8 | ForEach-Object {
  $ln = $_.Trim()
  if (-not $ln) { return }

  try { $obj = $ln | ConvertFrom-Json -ErrorAction Stop } catch { return }

  $ts = "$($obj.ts_trade)"
  if ($ts.Length -lt 10) { return }
  if ($ts.Substring(0,10) -ne $today) { return }

  $score = Get-EvProxy $obj
  $edge_ratio = $score
  $micro = Get-MicroScore $obj

  $evt = [ordered]@{
    as_of_date     = $today
    symbol         = "QQQ"
    source         = "REAL"
    score          = $score
    edge_ratio     = $edge_ratio
    micro_score    = $micro
    count_signals  = 1
    pnl_samples    = 2
  } | ConvertTo-Json -Compress

  Add-Content -Path $outJsonl -Value $evt -Encoding utf8
  $rows++
}

if ($rows -eq 0) {
  Write-Host "[GS-EVENTS] WARN: no QQQ rows for today; wrote empty $outJsonl" -ForegroundColor Yellow
  exit 0
}

Write-Host "[GS-EVENTS] Wrote $outJsonl rows=$rows mode=$Mode" -ForegroundColor Green
exit 0