[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA",

  [Parameter(Mandatory=$false)]
  [switch]$RequireRunContext
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# BLOCKG_SINGLE_SEMANTICS_OWNER
# Block-G is the single semantics owner for Phase-5 readiness.
# This script must NOT duplicate contract checks; it calls Check-BlockGReady and trusts exit code.
$checker = Join-Path (Split-Path -Parent $PSCommandPath) "Check-BlockGReady.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $Symbol | Out-Host
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

function Invoke-BlockGReady {
  [CmdletBinding()]
  param(
    [ValidateSet("NVDA","SPY","QQQ")]
    [string]$Symbol
  )
  $checker = Join-Path (Split-Path -Parent $PSCommandPath) "Check-BlockGReady.ps1"
  powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $Symbol | Out-Host
  return $LASTEXITCODE
}

function Fail-Contract([string]$Msg){
  [Console]::Error.WriteLine($Msg)
  exit 2
}
function Fail-Script([string]$Msg){
  [Console]::Error.WriteLine($Msg)
  exit 1
}
function To-StrictBool {
  param([Parameter(Mandatory=$true)]$Value)
  if($null -eq $Value){ return $false }
  if($Value -is [bool]){ return [bool]$Value }
  if($Value -is [string]){
    $v = $Value.Trim().ToLowerInvariant()
    if($v -in @("1","true","yes","y")){ return $true }
    if($v -in @("0","false","no","n")){ return $false }
  }
  return [bool]$Value
}
function Get-Date10([string]$s){
  if(-not $s){ return $null }
  $t = $s.Trim()
  if($t.Length -ge 10){ return $t.Substring(0,10) }
  return $t
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$today = (Get-Date).ToString("yyyy-MM-dd")


# ALL_MODE_PHASE5TODAY
if($Symbol -eq "ALL"){
  foreach($s in @("NVDA","SPY","QQQ")){
    powershell -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath -Symbol $s @(
      $(if($RequireRunContext){"-RequireRunContext"}else{$null})
    ) | Out-Host
    if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
  }
  exit 0
}
# -----------------------------------------------------------------------------
# 1) EV-hard daily CSV must include a today row with ok==true (fail-closed)
# -----------------------------------------------------------------------------
$csvPath = Join-Path $repoRoot "logs\phase5_ev_hard_veto_daily.csv"
if(-not (Test-Path $csvPath)){
  Fail-Contract "PHASE5: missing logs/phase5_ev_hard_veto_daily.csv"
}
try{
  $rows = Import-Csv -LiteralPath $csvPath
}catch{
  Fail-Script "PHASE5: failed to parse phase5_ev_hard_veto_daily.csv"
}

$hit = $null
foreach($r in $rows){
  $d = $null
  foreach($k in @("as_of_date","date","trading_day")){
    if($r.PSObject.Properties.Name -contains $k){
      $d = Get-Date10 ([string]$r.$k)
      break
    }
  }
  if($d -eq $today){ $hit = $r; break }
}
if($null -eq $hit){
  Fail-Contract "PHASE5: no today row in phase5_ev_hard_veto_daily.csv (today=$today)"
}

$ok = $false
foreach($k in @("ok","passed","computed_pass","ev_hard_ok_today")){
  if($hit.PSObject.Properties.Name -contains $k){
    $v = ([string]$hit.$k).Trim().ToLowerInvariant()
    if($v -in @("1","true","yes","y")){ $ok = $true }
    break
  }
}
if(-not $ok){
  Fail-Contract "PHASE5: EV-hard today row exists but ok flag is FALSE (today=$today)"
}

# -----------------------------------------------------------------------------
# 2) BlockG status JSON must be today + required fields true (contract-only)
# -----------------------------------------------------------------------------
$stPath = Join-Path $repoRoot "logs\blockg_status_stub.json"
if(-not (Test-Path $stPath)){
  Fail-Contract "PHASE5: missing logs/blockg_status_stub.json"
}
try{
  $raw = Get-Content -LiteralPath $stPath -Raw -Encoding UTF8
  $st = $raw | ConvertFrom-Json
}catch{
  Fail-Script "PHASE5: failed to parse blockg_status_stub.json"
}

$asOf = Get-Date10 ([string]$st.as_of_date)
if(-not $asOf){ Fail-Script "PHASE5: blockg_status_stub.json missing as_of_date" }
if($asOf -ne $today){
  Fail-Contract "PHASE5: blockg_status_stub.json stale as_of_date=$asOf today=$today"
}

# Required contract booleans
if(-not (To-StrictBool $st.phase23_health_ok_today)){ Fail-Contract "PHASE5: phase23_health_ok_today FALSE" }
if(-not (To-StrictBool $st.phase4_ok_today)){ Fail-Contract "PHASE5: phase4_ok_today FALSE" }
if(-not (To-StrictBool $st.ev_hard_daily_ok_today)){ Fail-Contract "PHASE5: ev_hard_daily_ok_today FALSE" }
if(-not (To-StrictBool $st.gatescore_fresh_today)){ Fail-Contract "PHASE5: gatescore_fresh_today FALSE" }

# Strict date fields (present in your status JSON)
$evAsOf = Get-Date10 ([string]$st.ev_hard_as_of_date)
if($evAsOf -and $evAsOf -ne $today){
  Fail-Contract "PHASE5: ev_hard_as_of_date stale ev_hard_as_of_date=$evAsOf today=$today"
}
$gsAsOf = Get-Date10 ([string]$st.gatescore_as_of_date)
if($gsAsOf -and $gsAsOf -ne $today){
  Fail-Contract "PHASE5: gatescore_as_of_date stale gatescore_as_of_date=$gsAsOf today=$today"
}

# Enforce per-symbol ready flag
switch ($Symbol.ToUpperInvariant()) {
  "NVDA" { $readyFlag = $st.nvda_blockg_ready }
  "SPY"  { $readyFlag = $st.spy_blockg_ready }
  "QQQ"  { $readyFlag = $st.qqq_blockg_ready }
  default { Fail-Contract "PHASE5: unknown symbol '$Symbol' for per-symbol check." }
}
if(-not (To-StrictBool $readyFlag)){
  Fail-Contract "PHASE5: per-symbol ready flag FALSE for $Symbol"
}

# -----------------------------------------------------------------------------
# 3) Optional: RunContext must be today (strong)
# -----------------------------------------------------------------------------
if($RequireRunContext){
  $rcPath = Join-Path $repoRoot "logs\run_context.json"
  if(-not (Test-Path $rcPath)){
    Fail-Contract "PHASE5: RequireRunContext set but logs/run_context.json missing"
  }
  try{
    $rcRaw = Get-Content -LiteralPath $rcPath -Raw -Encoding UTF8
    $rc = $rcRaw | ConvertFrom-Json
  }catch{
    Fail-Script "PHASE5: failed to parse run_context.json"
  }
  $rcAsOf = Get-Date10 ([string]$rc.as_of_date)
  if(-not $rcAsOf){ Fail-Script "PHASE5: run_context.json missing as_of_date" }
  if($rcAsOf -ne $today){
    Fail-Contract "PHASE5: run_context.json stale as_of_date=$rcAsOf today=$today"
  }
}

Write-Host "PHASE5: OK today ($today) symbol=$Symbol" -ForegroundColor Green
exit 0
