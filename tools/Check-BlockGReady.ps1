[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("NVDA","SPY","QQQ","ALL")]
    [string]$Symbol = "NVDA"
)


# ALL_MODE_BLOCKGREADY
if($Symbol -eq "ALL"){
  foreach($s in @("NVDA","SPY","QQQ")){
    & $PSCommandPath -Symbol $s
    if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
  }
  exit 0
}
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail-Contract([string]$Msg){
  [Console]::Error.WriteLine($Msg)
  exit 2
}

function Fail-Script([string]$Msg){
  [Console]::Error.WriteLine($Msg)
  exit 1
}

function Get-AsOfDateString {
  param([Parameter(Mandatory = $true)]$Payload)

  $props = $Payload.PSObject.Properties
  foreach ($name in @("as_of_date","date","trading_day")) {
    $prop = $props[$name]
    if ($prop -ne $null -and $prop.Value -ne $null -and $prop.Value -ne "") {
      $s = [string]$prop.Value
      return ($(if($s.Length -ge 10){ $s.Substring(0,10) } else { $s }))
    }
  }
  return $null
}

function To-StrictBool {
  param([Parameter(Mandatory = $true)]$Value)

  if ($null -eq $Value) { return $false }
  if ($Value -is [bool]) { return [bool]$Value }

  if ($Value -is [string]) {
    $v = $Value.Trim().ToLowerInvariant()
    if ($v -in @("1","true","yes","y"))  { return $true }
    if ($v -in @("0","false","no","n")) { return $false }
  }
  return [bool]$Value
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$logsStatus  = Join-Path $repoRoot "logs\blockg_status_stub.json"
$intelStatus = Join-Path $repoRoot ".intel\blockg_status_stub.json"

if (Test-Path $logsStatus) {
  $statusPath = $logsStatus
} elseif (Test-Path $intelStatus) {
  $statusPath = $intelStatus
} else {
  Fail-Contract "BLOCK-G: status JSON not found (.intel or logs)."
}

Write-Host "BLOCK-G: using status JSON at $statusPath" -ForegroundColor Cyan

try {
  $raw = Get-Content -Path $statusPath -Raw -Encoding UTF8
  $status = $raw | ConvertFrom-Json
} catch {
  Fail-Script "BLOCK-G: failed to parse status JSON at $statusPath."
}

$asOf = Get-AsOfDateString -Payload $status
if (-not $asOf) { Fail-Script "BLOCK-G: status JSON missing as_of_date/date/trading_day." }

$today = (Get-Date).ToString("yyyy-MM-dd")
if ($asOf -ne $today) { Fail-Contract "BLOCK-G: status JSON date mismatch. as_of_date=$asOf, today=$today." }

$phase23Ok = To-StrictBool $status.phase23_health_ok_today
$evHardOk  = To-StrictBool $status.ev_hard_daily_ok_today
$gsFresh   = To-StrictBool $status.gatescore_fresh_today


$phase4Ok = To-StrictBool $status.phase4_ok_today
$gsSamplesOk = To-StrictBool $status.gatescore_samples_ok
$gsThreshOk  = To-StrictBool $status.gatescore_threshold_ok_today

if (-not $phase4Ok)    { Fail-Contract "BLOCK-G: phase4_ok_today is FALSE." }
if (-not $gsSamplesOk) { Fail-Contract "BLOCK-G: gatescore_samples_ok is FALSE." }
if (-not $gsThreshOk)  { Fail-Contract "BLOCK-G: gatescore_threshold_ok_today is FALSE." }

# Optional (if present in payload, enforce; else ignore)
if ($status.PSObject.Properties.Name -contains "min_samples_ok_today") {
  $minSamplesOk = To-StrictBool $status.min_samples_ok_today
  if (-not $minSamplesOk) { Fail-Contract "BLOCK-G: min_samples_ok_today is FALSE." }
}
if (-not $phase23Ok) { Fail-Contract "BLOCK-G: phase23_health_ok_today is FALSE." }
if (-not $evHardOk)  { Fail-Contract "BLOCK-G: ev_hard_daily_ok_today is FALSE." }
if (-not $gsFresh)   { Fail-Contract "BLOCK-G: gatescore_fresh_today is FALSE." }

switch ($Symbol.ToUpperInvariant()) {
  "NVDA" { $readyFlag = $status.nvda_blockg_ready }
  "SPY"  { $readyFlag = $status.spy_blockg_ready }
  "QQQ"  { $readyFlag = $status.qqq_blockg_ready }
  default { Fail-Contract "BLOCK-G: unknown symbol '$Symbol' for Block-G check." }
}

if (-not (To-StrictBool $readyFlag)) { Fail-Contract "BLOCK-G: per-symbol ready flag is FALSE for $Symbol." }

Write-Host "BLOCK-G: READY for symbol=$Symbol (date=$asOf)." -ForegroundColor Green
exit 0
