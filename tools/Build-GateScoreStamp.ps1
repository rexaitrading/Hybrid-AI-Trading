[CmdletBinding()]
param(
  [string]$AsOf = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$today = (Get-Date).ToString("yyyy-MM-dd")
$asOf0 = ("" + $AsOf).Trim()
if(-not $asOf0){ $asOf0 = $today }

$csv = Join-Path $logsDir "gatescore_daily_summary.csv"
$outJson = Join-Path $logsDir "gatescore_stamp.json"

function To-Num($v){
  try { return [double]("" + $v) } catch { return [double]0 }
}

# thresholds (conservative; tune later via config)
$MIN_SIGNALS = 30
$MIN_PNL_SAMPLES = 30

$rowsToday = @()
$reasons = New-Object System.Collections.Generic.List[string]

if(-not (Test-Path -LiteralPath $csv)){
  [void]$reasons.Add("missing_gatescore_daily_summary_csv")
} else {
  try {
    $rows = @(Import-Csv -LiteralPath $csv)
    foreach($r in $rows){
      $d = ("" + $r.as_of_date).Trim()
      if($d -eq $asOf0){ $rowsToday += $r }
    }
  } catch {
    [void]$reasons.Add("gatescore_csv_read_failed")
  }
}

$rowcount = $rowsToday.Count
if($rowcount -eq 0){
  [void]$reasons.Add("no_gatescore_rows_today")
}

$perSymbol = @{}
foreach($sym in @("NVDA","SPY","QQQ")){
  $r = $null
  foreach($x in $rowsToday){
    if((("" + $x.symbol).Trim().ToUpper() -eq $sym)){ $r = $x }
  }

  $hasRow = ($null -ne $r)
  $countSignals = 0
  $pnlSamples = 0
  if($hasRow){
    $countSignals = [int](To-Num $r.count_signals)
    $pnlSamples   = [int](To-Num $r.pnl_samples)
  } else {
    [void]$reasons.Add(("gatescore_missing_symbol_row:{0}" -f $sym))
  }

  $minOk = $false
  if($hasRow){
    if(($countSignals -ge $MIN_SIGNALS) -and ($pnlSamples -ge $MIN_PNL_SAMPLES)){
      $minOk = $true
    } else {
      if($countSignals -lt $MIN_SIGNALS){ [void]$reasons.Add(("gatescore_min_signals_fail:{0}:{1}" -f $sym,$countSignals)) }
      if($pnlSamples -lt $MIN_PNL_SAMPLES){ [void]$reasons.Add(("gatescore_min_pnl_samples_fail:{0}:{1}" -f $sym,$pnlSamples)) }
    }
  }

  # Conservative stability placeholder: only "true" if min samples ok.
  # Never loosens readiness.
  $stable = $false
  if($minOk){ $stable = $true }

  $perSymbol[$sym] = [ordered]@{
    has_row        = [bool]$hasRow
    count_signals  = [int]$countSignals
    pnl_samples    = [int]$pnlSamples
    min_samples_ok = [bool]$minOk
    stable_today   = [bool]$stable
  }
}

$payload = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date = $asOf0
  gatescore_rows_today = [int]$rowcount
  per_symbol = $perSymbol
  gatescore_min_samples_ok_today = [bool]$perSymbol["NVDA"].min_samples_ok
  gatescore_stable_today = [bool]$perSymbol["NVDA"].stable_today
  reasons = @($reasons | Select-Object -Unique)
  version = "gatescore_stamp.1"
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$json = ($payload | ConvertTo-Json -Depth 8)
$json = ($json -replace "`r`n","`n").TrimEnd() + "`n"
[System.IO.File]::WriteAllText($outJson, $json, $utf8NoBom)

Write-Output $json
exit 0
