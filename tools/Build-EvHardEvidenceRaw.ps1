[CmdletBinding()]
param(
  [string]$OutPath = ".\logs\ev_hard_evidence_raw.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Utf8NoBom([string]$Path, [string]$Text) {
  $enc = New-Object System.Text.UTF8Encoding($false)
  $full = $Path
  if (-not [System.IO.Path]::IsPathRooted($full)) {
    $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
    $full = Join-Path $repoRoot $Path
  }
  $dir = Split-Path -Parent $full
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  [System.IO.File]::WriteAllText($full, $Text, $enc)
}

$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

# ---- Phase4 ----
$phase4Path = ".\logs\phase4_validation_passed.json"
$phase4Ok = $false
$phase4AsOf = ""
if (Test-Path $phase4Path) {
  try {
    $j = (Get-Content $phase4Path -Raw) | ConvertFrom-Json
    $phase4AsOf = (($j.as_of_date) + "").Trim()
    try { $phase4Ok = [bool]$j.ok } catch { $phase4Ok = $false }
  } catch {}
}

# ---- Phase23 ----
$phase23Path = ".\logs\phase23_health_daily.csv"
$phase23Ok = $false
$phase23AsOf = ""
if (Test-Path $phase23Path) {
  try {
    $rows = @(Import-Csv $phase23Path)
    if ($rows.Count -gt 0) {
      $last = $rows | Sort-Object as_of_date | Select-Object -Last 1
      $phase23AsOf = (($last.as_of_date) + "").Trim()
      try { $phase23Ok = [bool]$last.ok } catch { $phase23Ok = $false }
    }
  } catch {}
}

# ---- GateScore ----
$gsPath = ".\logs\gatescore_daily_summary.csv"
$gsOk = $false
$gsAsOf = ""
if (Test-Path $gsPath) {
  try {
    $rows = @(Import-Csv $gsPath)
    $row = $rows | Where-Object { $_.symbol -eq "NVDA" -and ($_.as_of_date + "") -eq $today } | Select-Object -First 1
    if ($null -ne $row) {
      $gsAsOf = (($row.as_of_date) + "").Trim()
      # ok if thresholds/samples satisfied implicitly by existence of today row and count_signals>0
      $cs = 0
      [void][int]::TryParse([string]$row.count_signals, [ref]$cs)
      $gsOk = ($cs -gt 0)
    }
  } catch {}
}

# ---- Decision (fail-closed) ----
$ok = $false
$reason = "missing_inputs_failclosed"
$reasons = New-Object System.Collections.Generic.List[string]

if ($phase4AsOf -ne $today -or -not $phase4Ok) { $reasons.Add("phase4_not_ok_or_stale") }
if ($phase23AsOf -ne $today -or -not $phase23Ok) { $reasons.Add("phase23_not_ok_or_stale") }
if ($gsAsOf -ne $today -or -not $gsOk) { $reasons.Add("gatescore_not_ok_or_missing_today_row") }

if ($reasons.Count -eq 0) {
  $ok = $true
  $reason = "raw_inputs_all_green"
} else {
  $ok = $false
  $reason = ($reasons -join ";")
}

$out = [ordered]@{
  ts_utc = $tsUtc
  as_of_date = $today
  ok = $ok
  reason = $reason
  inputs = [ordered]@{
    phase4 = [ordered]@{ as_of_date=$phase4AsOf; ok=$phase4Ok; path=$phase4Path }
    phase23 = [ordered]@{ as_of_date=$phase23AsOf; ok=$phase23Ok; path=$phase23Path }
    gatescore = [ordered]@{ as_of_date=$gsAsOf; ok=$gsOk; path=$gsPath; symbol="NVDA" }
  }
} | ConvertTo-Json -Depth 8

Write-Utf8NoBom -Path $OutPath -Text ($out + "`n")
Write-Host ("[EV-HARD-RAW] wrote {0} ok={1} reason={2}" -f $OutPath,$ok,$reason) -ForegroundColor Cyan
exit 0
