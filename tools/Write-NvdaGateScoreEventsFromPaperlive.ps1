[CmdletBinding()]
param(
  [ValidateSet("REAL")]
  [string]$Mode = "REAL",

  [Parameter(Mandatory=$false)]
  [string]$AsOfDate = ""
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logs  = Join-Path $repoRoot "logs"

# Phase-2 micro snapshot (day-level) -> micro_score fallback (fail-closed to 0.0)
$pyExe = Join-Path $repoRoot ".\.venv\Scripts\python.exe"
$microFallback = 0.0
try {
  if (Test-Path $pyExe -and (Test-Path ".\tools\compute_nvda_micro_score_today.py")) {
    $out = & $pyExe ".\tools\compute_nvda_micro_score_today.py"
    $microFallback = [double]("$out")
  }
} catch { $microFallback = 0.0 }

$today = if ([string]::IsNullOrWhiteSpace($AsOfDate)) { (Get-Date).ToString("yyyy-MM-dd") } else { $AsOfDate }

# Phase-2 micro snapshot (day-level) -> micro_score fallback
$pyExe = Join-Path $repoRoot ".\.venv\Scripts\python.exe"
$microFallback = 0.0
try {
  if (Test-Path $pyExe -and (Test-Path ".\tools\compute_nvda_micro_score_today.py")) {
    $out = & $pyExe ".\tools\compute_nvda_micro_score_today.py"
    $microFallback = [double]("$out")
  }
} catch { $microFallback = 0.0 }


# NVDA paperlive results (canonical path)
$inJsonl  = Join-Path $logs "nvda_phase5_paperlive_results.jsonl"
$outJsonl = Join-Path $logs "nvda_gatescore_events.jsonl"

if (-not (Test-Path $inJsonl)) { throw "Missing input: $inJsonl" }

# overwrite daily (deterministic) - ensure empty file, no blank first line JSONL issues
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outJsonl, "", $utf8NoBom)

function Get-EvProxy($obj) {
  # prefer top-level ev
  try {
    if ($null -ne $obj -and $obj.PSObject -and ($obj.PSObject.Properties.Name -contains "ev")) {
      $v = $obj.PSObject.Properties["ev"].Value
      if ($null -ne $v) { return [double]("$v") }
    }
  } catch { }

  # prefer phase5_result.details.ev_mu / phase5_details.ev_mu
  try {
    if ($null -ne $obj.phase5_result) {
      $d = $obj.phase5_result.phase5_details
      if ($null -eq $d) { $d = $obj.phase5_result.details }
      if ($null -ne $d -and $null -ne $d.ev_mu) { return [double]("$($d.ev_mu)") }
    }
  } catch { }

  return $null
}
function Get-EdgeRatio($obj) {
  try {
    if ($null -ne $obj -and $obj.PSObject -and ($obj.PSObject.Properties.Name -contains "edge_ratio")) {
      $v = $obj.PSObject.Properties["edge_ratio"].Value
      if ($null -ne $v) { return [double]("$v") }
    }
  } catch { }
  return 0.0
}

function Get-MicroScore($obj) {
  try {
    if ($null -ne $obj -and $obj.PSObject -and ($obj.PSObject.Properties.Name -contains "micro_score")) {
      $v = $obj.PSObject.Properties["micro_score"].Value
      if ($null -ne $v) { return [double]("$v") }
    }
  } catch { }
  return 0.0
}

function Has-RealizedPnl($obj) {
  try {
    if ($null -ne $obj -and $obj.PSObject -and ($obj.PSObject.Properties.Name -contains "realized_pnl")) {
      return $true
    }
  } catch { }
  return $false
}

$rows = 0
Get-Content $inJsonl -Encoding utf8 | ForEach-Object {
  $ln = $_.Trim()
  if (-not $ln) { return }

  try { $obj = $ln | ConvertFrom-Json -ErrorAction Stop } catch { return }

  # StrictMode-safe: use ts_trade (your NVDA paperlive has it)
  $ts = ""
  try {
    if ($obj.PSObject.Properties.Name -contains "ts_trade") {
      $ts = "$($obj.PSObject.Properties["ts_trade"].Value)"
    }
  } catch { $ts = "" }

  if ($ts.Length -lt 10) { return }
  if ($ts.Substring(0,10) -ne $today) { return }

  # Only count events that have GateScore metrics (edge_ratio + micro_score) AND a realized_pnl field
  $edge = (Get-EvProxy $obj); if ($null -eq $edge) { $edge = Get-EdgeRatio $obj }
  $micro = Get-MicroScore $obj; if ($micro -le 0.0) { $micro = $microFallback }
  if ($edge -eq 0.0 -and $micro -eq 0.0) { return }
  if (-not (Has-RealizedPnl $obj)) { return }

  $evt = [ordered]@{
    as_of_date     = $today
    symbol         = "NVDA"
    source         = "REAL"
    score          = $edge   # conservative placeholder: score mirrors edge_ratio (until true model score is wired)
    edge_ratio     = $edge
    micro_score    = $micro
    count_signals  = 1
    pnl_samples    = 1
    notes          = "authoritative_from_nvda_paperlive"
  } | ConvertTo-Json -Compress

  Add-Content -Path $outJsonl -Value $evt -Encoding utf8
  $rows++
}

if ($rows -eq 0) {
  Write-Host "[GS-EVENTS] WARN: no NVDA events for today (edge/micro/realized_pnl missing); wrote empty $outJsonl" -ForegroundColor Yellow
  exit 0
}

Write-Host "[GS-EVENTS] Wrote $outJsonl rows=$rows mode=$Mode" -ForegroundColor Green
exit 0




