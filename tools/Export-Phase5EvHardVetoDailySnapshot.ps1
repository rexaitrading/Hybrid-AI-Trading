[CmdletBinding()]
param(
  [string]$InputPath = ".\.hat\inputs\phase5_ev_hard_veto_snapshot_input.json",
  [string]$SnapshotOut = ".\logs\phase5_ev_hard_veto_snapshot.json",
  [string]$EvidenceOut = ".\logs\ev_hard_snapshot.json",
  [string]$DailyCsv = ".\logs\phase5_ev_hard_veto_daily.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function As-Bool([object]$v) {
  if ($null -eq $v) { return $false }
  if ($v -is [bool]) { return [bool]$v }
  $s = ("" + $v).Trim()
  return ($s -in @("1","true","True","TRUE","yes","YES"))
}

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
# --- A3: market-aware TODAY (prefer HAT_ASOF_DATE, else Resolve-RunContext when HAT_MARKET is set) ---
$today = (Get-Date).ToString("yyyy-MM-dd")
try {
  $asofEnv = (($env:HAT_ASOF_DATE + "")).Trim()
  if($asofEnv){
    $asofEnv = $asofEnv.Substring(0,[Math]::Min(10,$asofEnv.Length))
    if($asofEnv -match '^\d{4}-\d{2}-\d{2}$'){ $today = $asofEnv }
  } else {
    $m = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant()
    if($m){
      $sym = (($env:HAT_SYMBOL + "")).Trim().ToUpperInvariant()
      if(-not $sym){ $sym = "NVDA" }
      $rcPath = Join-Path $repoRoot "tools\Resolve-RunContext.ps1"
      if(Test-Path -LiteralPath $rcPath){
        $raw = (& $rcPath -Market $m -Symbol $sym | Out-String).Trim()
        $i0=$raw.IndexOf("{"); $i1=$raw.LastIndexOf("}")
        if($i0 -ge 0 -and $i1 -gt $i0){
          $rc = ($raw.Substring($i0, ($i1-$i0+1))) | ConvertFrom-Json
          if($rc -and $rc.as_of_date){
            $d = ([string]$rc.as_of_date).Trim()
            if($d.Length -ge 10){ $today = $d.Substring(0,10) }
          }
        }
      }
    }
  }
} catch { }
# --- A3 END ---
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

