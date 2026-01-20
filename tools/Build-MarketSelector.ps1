[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")][string]$Market = "US",
  [ValidateSet("NVDA","SPY","QQQ")][string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $toolsDir) -ErrorAction Stop).Path
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

function Slice10([string]$s){ $s=(($s+"")).Trim(); if($s.Length -ge 10){ return $s.Substring(0,10) } return $s }

# RunContext is single truth for as_of_date + session + logs_dir_out
$rcPath = Join-Path $repoRoot "tools\Resolve-RunContext.ps1"
if(-not (Test-Path -LiteralPath $rcPath)){ throw "[FAIL-CLOSED] missing Resolve-RunContext.ps1" }
$rcRaw = & $rcPath -Market $Market -Symbol $Symbol 2>$null | Out-String
$rcRaw = (($rcRaw+"")).Trim()
$i0 = $rcRaw.IndexOf("{"); $i1 = $rcRaw.LastIndexOf("}")
if($i0 -lt 0 -or $i1 -le $i0){ throw "[FAIL-CLOSED] Resolve-RunContext did not return JSON" }
$rc = ($rcRaw.Substring($i0, ($i1-$i0+1)) | ConvertFrom-Json -ErrorAction Stop)

$todayLocal = Slice10 ([string]$rc.as_of_date)
$logsDirOut = ""
try { if($rc.PSObject.Properties.Name -contains "logs_dir_out"){ $logsDirOut = ([string]$rc.logs_dir_out).Trim() } } catch { $logsDirOut = "" }
if(-not $logsDirOut){ try { if($rc.PSObject.Properties.Name -contains "logs_dir"){ $logsDirOut = ([string]$rc.logs_dir).Trim() } } catch { $logsDirOut = "" } }
if(-not $todayLocal){ throw "[FAIL-CLOSED] todayLocal empty" }
if(-not $logsDirOut){ throw "[FAIL-CLOSED] logsDirOut empty" }
New-Item -ItemType Directory -Force -Path $logsDirOut | Out-Null

# MARKET_ENABLEMENT_RECEIPT_V1
$enablePath = Join-Path $logsDirOut "market_enablement.json"
$marketEnabled = $false
$enableReason = "missing_market_enablement_receipt"
$allowedModules = @()
if(Test-Path -LiteralPath $enablePath){
  try {
    $enObj = (Get-Content -LiteralPath $enablePath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop)
    try { if($enObj.PSObject.Properties.Name -contains "enabled"){ $marketEnabled = [bool]$enObj.enabled } } catch { $marketEnabled = $false }
    try { if($enObj.PSObject.Properties.Name -contains "reason"){ $enableReason = ([string]$enObj.reason) } else { $enableReason = "receipt_present" } } catch { $enableReason = "receipt_present" }
    try { if($enObj.PSObject.Properties.Name -contains "allowed_modules"){ $allowedModules = @($enObj.allowed_modules) } } catch { $allowedModules = @() }
  } catch {
    $marketEnabled = $false
    $enableReason = "enablement_receipt_parse_failed"
  }
} else {
  $marketEnabled = $false
}


# Default fail-closed: NO_TRADE
$decision = "NO_TRADE"
$chosenMarket = ""
$chosenModule = ""
$reason = "not_enabled_market_v2"
$okToday = $true

# US-only v1: TRADE only when ALL prereqs are green (audit-only; no enforcement yet)
if($marketEnabled){
if((($Market+"")).Trim().ToUpperInvariant() -eq "US"){
  $chosenMarket = "US"
  $chosenModule = "US_VWAP_Overnight_Reversion"
  $reason = "default_no_trade"

  $stubPath = Join-Path $logsDirOut "blockg_status_stub.json"
  $st = $null
  if(Test-Path -LiteralPath $stubPath){
    try { $st = (Get-Content -LiteralPath $stubPath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop) } catch { $st = $null }
  }

  $sessionOk = $false; $openOk = $false; $closedOk = $true
  $intelOk = $false; $regimeOk = $false; $globalOk = $false; $gsFresh = $false

  try { if($rc.PSObject.Properties.Name -contains "session_name"){ $sessionOk = (([string]$rc.session_name).Trim().ToUpperInvariant() -eq "RTH") } } catch { $sessionOk = $false }
  try { if($rc.PSObject.Properties.Name -contains "is_open_now"){ $openOk = [bool]$rc.is_open_now } } catch { $openOk = $false }
  try { if($rc.PSObject.Properties.Name -contains "market_closed_today"){ $closedOk = (-not [bool]$rc.market_closed_today) } } catch { $closedOk = $false }

  if($st){
    try { if($st.PSObject.Properties.Name -contains "intel_ok_today"){ $intelOk = [bool]$st.intel_ok_today } } catch { $intelOk = $false }
    try { if($st.PSObject.Properties.Name -contains "regime_ok_today"){ $regimeOk = [bool]$st.regime_ok_today } } catch { $regimeOk = $false }
    try { if($st.PSObject.Properties.Name -contains "global_ready_ok_today"){ $globalOk = [bool]$st.global_ready_ok_today } } catch { $globalOk = $false }
    try { if($st.PSObject.Properties.Name -contains "gatescore_fresh_today"){ $gsFresh = [bool]$st.gatescore_fresh_today } } catch { $gsFresh = $false }
  } else {
    $reason = "missing_blockg_status_stub"
  }

  if($sessionOk -and $openOk -and $closedOk -and $intelOk -and $regimeOk -and $globalOk -and $gsFresh){
    $decision = "TRADE"
    $reason = "all_prereqs_green"
  } else {
    if(-not $sessionOk){ $reason = "session_not_rth" }
    elseif(-not $openOk){ $reason = "market_is_open_now=false" }
    elseif(-not $closedOk){ $reason = "market_closed_today=true" }
    elseif(-not $intelOk){ $reason = "intel_ok_today=false" }
    elseif(-not $regimeOk){ $reason = "regime_ok_today=false" }
    elseif(-not $globalOk){ $reason = "global_ready_ok_today=false" }
    elseif(-not $gsFresh){ $reason = "gatescore_fresh_today=false" }
  }
}
elseif((($Market+"")).Trim().ToUpperInvariant() -eq "JP"){
  $chosenMarket = "JP"
  $chosenModule = "JP_Opening_Overreaction_Fade"
  $reason = "default_no_trade"

  # Read latest BlockG stub if present (audit-only prereq source)
  $stubPath = Join-Path $logsDirOut "blockg_status_stub.json"
  $st = $null
  if(Test-Path -LiteralPath $stubPath){
    try { $st = (Get-Content -LiteralPath $stubPath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop) } catch { $st = $null }
  }

  $sessionOk = $false; $openOk = $false; $closedOk = $true
  $intelOk = $false; $regimeOk = $false; $globalOk = $false; $gsFresh = $false

  try { if($rc.PSObject.Properties.Name -contains "session_name"){ $sessionOk = (([string]$rc.session_name).Trim().ToUpperInvariant() -eq "RTH") } } catch { $sessionOk = $false }
  try { if($rc.PSObject.Properties.Name -contains "is_open_now"){ $openOk = [bool]$rc.is_open_now } } catch { $openOk = $false }
  try { if($rc.PSObject.Properties.Name -contains "market_closed_today"){ $closedOk = (-not [bool]$rc.market_closed_today) } } catch { $closedOk = $false }

  if($st){
    try { if($st.PSObject.Properties.Name -contains "intel_ok_today"){ $intelOk = [bool]$st.intel_ok_today } } catch { $intelOk = $false }
    try { if($st.PSObject.Properties.Name -contains "regime_ok_today"){ $regimeOk = [bool]$st.regime_ok_today } } catch { $regimeOk = $false }
    try { if($st.PSObject.Properties.Name -contains "global_ready_ok_today"){ $globalOk = [bool]$st.global_ready_ok_today } } catch { $globalOk = $false }
    try { if($st.PSObject.Properties.Name -contains "gatescore_fresh_today"){ $gsFresh = [bool]$st.gatescore_fresh_today } } catch { $gsFresh = $false }
  } else {
    $reason = "missing_blockg_status_stub"
  }

  if($sessionOk -and $openOk -and $closedOk -and $intelOk -and $regimeOk -and $globalOk -and $gsFresh){
    $decision = "TRADE"
    $reason = "all_prereqs_green"
  } else {
    if(-not $sessionOk){ $reason = "session_not_rth" }
    elseif(-not $openOk){ $reason = "market_is_open_now=false" }
    elseif(-not $closedOk){ $reason = "market_closed_today=true" }
    elseif(-not $intelOk){ $reason = "intel_ok_today=false" }
    elseif(-not $regimeOk){ $reason = "regime_ok_today=false" }
    elseif(-not $globalOk){ $reason = "global_ready_ok_today=false" }
    elseif(-not $gsFresh){ $reason = "gatescore_fresh_today=false" }
  }
}

  # ENABLEMENT_ALLOWLIST_V1
  $allowList = @($allowedModules)
  if($allowList.Count -le 0){
    $decision = "NO_TRADE"
    $reason = "no_allowed_modules"
    $chosenMarket = ""
    $chosenModule = ""
  } elseif(-not $chosenModule -or -not ($allowList -contains $chosenModule)){
    $decision = "NO_TRADE"
    $reason = ("module_not_allowlisted:" + (($chosenModule + "")).Trim())
    $chosenMarket = ""
    $chosenModule = ""
  }

} else {
  # Not enabled => hard NO_TRADE (receipt-backed)
  $decision = "NO_TRADE"
  $chosenMarket = ""
  $chosenModule = ""
  if(($enableReason + "").Trim()){ $reason = "not_enabled_market_v2:" + (($enableReason + "")).Trim() } else { $reason = "not_enabled_market_v2" }
}

$out = [ordered]@{
  schema = "market_selector.v1"
  market = (($Market+"")).Trim().ToUpperInvariant()
  as_of_date = $todayLocal
  ok_today = [bool]$okToday
  strict_no_trade = $true
  decision = $decision
  chosen_market = $chosenMarket
  chosen_module = $chosenModule
  reason = $reason
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  details = [ordered]@{
    session_name = ([string]$rc.session_name)
    market_is_open_now = [bool]$rc.is_open_now
    market_closed_today = [bool]$rc.market_closed_today
  }
}

$outPath = Join-Path $logsDirOut "market_selector.json"
[System.IO.File]::WriteAllText($outPath, (($out | ConvertTo-Json -Depth 8) + "`n"), (New-Object System.Text.UTF8Encoding($false)))
Write-Host ("[MKT_SELECTOR] wrote " + $outPath + " decision=" + $decision + " reason=" + $reason) -ForegroundColor Cyan
exit 0
