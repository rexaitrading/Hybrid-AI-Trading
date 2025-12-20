[CmdletBinding()]
param(
  [string]$InputPath = ".\.hat\inputs\phase5_ev_hard_veto_snapshot_input.json",
  [string]$SnapshotOut = ".\logs\phase5_ev_hard_veto_snapshot.json",
  [string]$EvidenceOut = ".\logs\phase5_ev_hard_veto_evidence.json",
  [string]$DailyCsv = ".\logs\phase5_ev_hard_veto_daily.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Utf8NoBom {
  param([string]$Path, [string]$Text)
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

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

$ok = $false
$reason = "snapshot_input_missing_failclosed"

if (Test-Path $InputPath) {
  $raw = Get-Content $InputPath -Raw
  $inp = $raw | ConvertFrom-Json

  # strict computed schema
  $props = $inp.PSObject.Properties.Name
  if ($props -contains "ev_hard_veto_live_enabled") {
    $enabled = [bool]$inp.ev_hard_veto_live_enabled
    if (-not $enabled) {
      $ok = $false; $reason = "ev_hard_veto_disabled_failclosed"
    } else {
      if ($props -contains "computed_pass") {
        $ok = [bool]$inp.computed_pass
        if ($props -contains "computed_reason" -and (($inp.computed_reason + "") -ne "")) {
          $reason = [string]$inp.computed_reason
        } else {
          $reason = "computed_from_inputs"
        }
      } else {
        $ok = $false; $reason = "computed_pass_missing_failclosed"
      }
    }
  } else {
    $ok = $false; $reason = "ev_hard_veto_live_enabled_missing_failclosed"
  }
}

$snap = [ordered]@{
  ts_utc = $tsUtc
  as_of_date = $today
  ok = $ok
  reason = $reason
  inputs = @{ input = $InputPath }
} | ConvertTo-Json -Depth 8

$evi = [ordered]@{
  ts_utc = $tsUtc
  as_of_date = $today
  ok = $ok
  reason = $reason
  inputs = @{ source = (Split-Path -Leaf $SnapshotOut) }
} | ConvertTo-Json -Depth 8

Write-Utf8NoBom -Path $SnapshotOut -Text ($snap + "`n")
Write-Utf8NoBom -Path $EvidenceOut -Text ($evi + "`n")

if (-not (Test-Path $DailyCsv)) { Write-Utf8NoBom -Path $DailyCsv -Text ("date,ok,reason`n") }

$rows = @()
try { $rows = @(Import-Csv $DailyCsv) } catch { $rows = @() }
$rows = @($rows | Where-Object { $_.date -ne $today })
$rows += [pscustomobject]@{ date=$today; ok=$ok; reason=$reason }

$csv = "date,ok,reason`n" + (($rows | Sort-Object date | ForEach-Object { '{0},{1},{2}' -f $_.date,$_.ok,$_.reason }) -join "`n") + "`n"
Write-Utf8NoBom -Path $DailyCsv -Text $csv

Write-Host ("[EV-HARD] as_of_date={0} ok={1} reason={2}" -f $today,$ok,$reason) -ForegroundColor Cyan
exit 0
