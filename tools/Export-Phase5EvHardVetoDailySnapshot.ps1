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
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText((Resolve-Path $Path).Path, $Text, $utf8NoBom)
}

$repoRoot = (Resolve-Path ".").Path
$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

$ok = $false
$reason = "missing_inputs_failclosed"

if(Test-Path $InputPath){
  $raw = Get-Content $InputPath -Raw
  $inp = $raw | ConvertFrom-Json

  # ===== REAL LOGIC HOOK =====
  # For now we enforce: operator override is NOT allowed as a reason to become ok=True.
  # Replace below with your real conditions (EV-band hard veto, regime, etc.).
  if($inp.PSObject.Properties.Name -contains "ev_hard_veto_live_enabled"){
    $enabled = [bool]$inp.ev_hard_veto_live_enabled
    if($enabled){
      # Example: if enabled, require explicit computed_pass==true in input
      if($inp.PSObject.Properties.Name -contains "computed_pass"){
        $ok = [bool]$inp.computed_pass
        $reason = "computed_from_inputs"
      } else {
        $ok = $false
        $reason = "computed_pass_missing_failclosed"
      }
    } else {
      # If veto system disabled, we still fail-closed for LIVE readiness
      $ok = $false
      $reason = "ev_hard_veto_disabled_failclosed"
    }
  } else {
    $ok = $false
    $reason = "ev_hard_veto_live_enabled_missing_failclosed"
  }
} else {
  $ok = $false
  $reason = "snapshot_input_missing_failclosed"
}

# Snapshot JSON
$snap = [ordered]@{
  ts_utc = $tsUtc
  as_of_date = $today
  ok = $ok
  reason = $reason
  inputs = @{ input = $InputPath }
} | ConvertTo-Json -Depth 8

# Evidence JSON (simple chain-of-custody)
$evi = [ordered]@{
  ts_utc = $tsUtc
  as_of_date = $today
  ok = $ok
  reason = $reason
  inputs = @{ source = (Split-Path -Leaf $SnapshotOut) }
} | ConvertTo-Json -Depth 8

Write-Utf8NoBom -Path $SnapshotOut -Text ($snap + "`n")
Write-Utf8NoBom -Path $EvidenceOut -Text ($evi + "`n")

# Daily CSV upsert (date,ok,reason)
if(-not (Test-Path $DailyCsv)){
  Write-Utf8NoBom -Path $DailyCsv -Text ("date,ok,reason`n")
}

$rows = Import-Csv $DailyCsv
$rows = @($rows | Where-Object { $_.date -ne $today })
$rows += [pscustomobject]@{ date=$today; ok=$ok; reason=$reason }

# Write back
$csv = "date,ok,reason`n" + (($rows | Sort-Object date | ForEach-Object {
  '{0},{1},{2}' -f $_.date, $_.ok, $_.reason
}) -join "`n") + "`n"
Write-Utf8NoBom -Path $DailyCsv -Text $csv

Write-Host ("[EV-HARD] as_of_date={0} ok={1} reason={2}" -f $today,$ok,$reason) -ForegroundColor Cyan
