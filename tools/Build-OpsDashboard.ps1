[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",

  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [ValidateSet("PAPER","PAPERLIVE","LIVE")]
  [string]$Mode = "",

  [string]$OutPath = "",

  [switch]$EmitConsole = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- UTF-8 output (institutional) ---
try {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding  = $utf8
  $global:OutputEncoding    = $utf8
} catch { }

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $t = ($Text -replace "`r`n","`n" -replace "`r","`n")
  if($t.Length -eq 0 -or $t[-1] -ne "`n"){ $t += "`n" }
  [System.IO.File]::WriteAllText($Path, $t, (New-Object System.Text.UTF8Encoding($false)))
}

function Fail([string]$m){
  Write-Host ("[FAIL-CLOSED] " + $m) -ForegroundColor Red
  exit 2
}

function Slice10([string]$d){
  $s = ([string]$d).Trim()
  if($s.Length -ge 10){ return $s.Substring(0,10) }
  return $s
}

function Read-JsonSafe([string]$Path){
  try{
    if(-not (Test-Path -LiteralPath $Path)){ return $null }
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if(-not $raw){ return $null }
    return ($raw | ConvertFrom-Json -ErrorAction Stop)
  } catch { return $null }
}

function BoolProp([object]$obj,[string]$name,[bool]$default){
  try{
    if($null -eq $obj){ return $default }
    if($obj.PSObject.Properties.Name -contains $name){ return [bool]$obj.$name }
    return $default
  } catch { return $default }
}

# --- repoRoot (filesystem truth) ---
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
try { $repoRoot = (Resolve-Path -LiteralPath $repoRoot -ErrorAction Stop).Path } catch { }

# --- Resolve run_mode (single truth) ---
$rmPath = Join-Path $toolsDir "Resolve-HatRunMode.ps1"
if(-not (Test-Path -LiteralPath $rmPath)){ Fail ("missing Resolve-HatRunMode.ps1: " + $rmPath) }
$rmRaw = (& $rmPath 2>&1 | Out-String).Trim()
$i0 = $rmRaw.IndexOf('{'); $i1 = $rmRaw.LastIndexOf('}')
if($i0 -lt 0 -or $i1 -le $i0){ Fail "Resolve-HatRunMode did not return JSON" }
$rm = ($rmRaw.Substring($i0, ($i1-$i0+1)) | ConvertFrom-Json -ErrorAction Stop)
$runMode = ([string]$rm.run_mode).Trim().ToUpperInvariant()
if($Mode){
  $m2 = ($Mode + "").Trim().ToUpperInvariant()
  if($m2 -notin @("PAPER","PAPERLIVE","LIVE")){ Fail ("invalid -Mode=" + $Mode) }
  $runMode = $m2
}

# --- Policy A: non-US markets only support NVDA ---
$mk = ($Market + "").Trim().ToUpperInvariant()
$sy = ($Symbol + "").Trim().ToUpperInvariant()
if($mk -ne "US" -and $sy -in @("SPY","QQQ")){
  Fail ("PolicyA symbol_not_applicable_for_market market=" + $mk + " symbol=" + $sy)
}

# --- Resolve RunContext (A3 single truth) ---
$rcPath = Join-Path $toolsDir "Resolve-RunContext.ps1"
if(-not (Test-Path -LiteralPath $rcPath)){ Fail ("missing Resolve-RunContext.ps1: " + $rcPath) }
$rcRaw = (& $rcPath -Market $mk -Symbol $sy 2>&1 | Out-String).Trim()
$j0 = $rcRaw.IndexOf('{'); $j1 = $rcRaw.LastIndexOf('}')
if($j0 -lt 0 -or $j1 -le $j0){ Fail ("Resolve-RunContext did not return JSON market=" + $mk) }
$rc = ($rcRaw.Substring($j0, ($j1-$j0+1)) | ConvertFrom-Json -ErrorAction Stop)

if(-not ($rc.PSObject.Properties.Name -contains "as_of_date")){ Fail "RunContext missing as_of_date" }
if(-not ($rc.PSObject.Properties.Name -contains "logs_dir_out")){ Fail "RunContext missing logs_dir_out" }

$asOf = Slice10 ([string]$rc.as_of_date)
$logsDirOut = ([string]$rc.logs_dir_out).Trim()
if(-not $logsDirOut){ Fail "RunContext logs_dir_out empty" }

# invariant: logs_dir_out must match market
$viol = New-Object System.Collections.Generic.List[string]
$mkNeed = ("\logs\" + $mk + "\").ToLowerInvariant()
if((($logsDirOut -replace "/","\") + "\").ToLowerInvariant().IndexOf($mkNeed) -lt 0){
  $viol.Add(("logs_dir_out_market_mismatch logs_dir_out=" + $logsDirOut + " market=" + $mk)) | Out-Null
}
if($mk -ne "US" -and (($logsDirOut -replace "/","\") -match "\\logs\\US(\\|$)")){
  $viol.Add(("us_log_bleed logs_dir_out=" + $logsDirOut + " market=" + $mk)) | Out-Null
}

# default OutPath
if(-not $OutPath){
  $OutPath = Join-Path $logsDirOut "ops_dashboard.json"
}

# --- A2 status reads ---
function Read-A2Status([string]$Path,[string]$Today){
  $o = [ordered]@{
    present = $false
    as_of_date = ""
    ok_today = $false
    not_eval_closed = $false
    reason = ""
  }
  $j = Read-JsonSafe $Path
  if(-not $j){ return $o }
  $o.present = $true
  if($j.PSObject.Properties.Name -contains "as_of_date"){ $o.as_of_date = Slice10 ([string]$j.as_of_date) }
  if($j.PSObject.Properties.Name -contains "ok_today"){ $o.ok_today = [bool]$j.ok_today }
  if($j.PSObject.Properties.Name -contains "not_evaluated_market_closed"){ $o.not_eval_closed = [bool]$j.not_evaluated_market_closed }
  if($j.PSObject.Properties.Name -contains "reason"){ $o.reason = [string]$j.reason }
  return $o
}

$p4 = Read-A2Status (Join-Path $logsDirOut "phase4_status.json") $asOf
$p23 = Read-A2Status (Join-Path $logsDirOut "phase23_status.json") $asOf
$evh = Read-A2Status (Join-Path $logsDirOut "ev_hard_status.json") $asOf

# --- BlockG stub read ---
$stubPath = Join-Path $logsDirOut "blockg_status_stub.json"
$st = Read-JsonSafe $stubPath
$stubPresent = ($null -ne $st)

if(-not $stubPresent){
  $viol.Add(("missing_blockg_stub path=" + $stubPath)) | Out-Null
}

# Extract minimal blockg fields (StrictMode-safe)
$sem = ""; $semr = ""
$nvReady = $false; $spyReady = $false; $qqqReady = $false
$top = ""
try {
  if($stubPresent){
    if($st.PSObject.Properties.Name -contains "contract_semantics_level"){ $sem = [string]$st.contract_semantics_level }
    if($st.PSObject.Properties.Name -contains "contract_semantics_reason"){ $semr = [string]$st.contract_semantics_reason }
    $nvReady = BoolProp $st "nvda_blockg_ready" $false
    $spyReady = BoolProp $st "spy_blockg_ready" $false
    $qqqReady = BoolProp $st "qqq_blockg_ready" $false
    if($st.PSObject.Properties.Name -contains "reasons_not_ready"){
      $rr = @($st.reasons_not_ready)
      if($rr.Count -gt 0){ $top = (($rr[0] + "")).Trim() }
    }
  }
} catch { }

# --- Risk snapshot (diagnostic only; kill logic later) ---
$risk = [ordered]@{
  riskcap_present = $false
  daily_loss_cap_usd = 0
  cooldown_minutes = 0
  crisis_regime = $false
  portfolio_halt = $false
  risk_flatten = $false
}

# crisis status if present
try {
  $cj = Read-JsonSafe (Join-Path $logsDirOut "crisis_regime_status.json")
  if($cj){
    if($cj.PSObject.Properties.Name -contains "crisis_regime"){ $risk.crisis_regime = [bool]$cj.crisis_regime }
    if($cj.PSObject.Properties.Name -contains "portfolio_halt"){ $risk.portfolio_halt = [bool]$cj.portfolio_halt }
    if($cj.PSObject.Properties.Name -contains "risk_flatten"){ $risk.risk_flatten = [bool]$cj.risk_flatten }
    if($cj.PSObject.Properties.Name -contains "cooldown_minutes"){
      try { $risk.cooldown_minutes = [int]$cj.cooldown_minutes } catch { $risk.cooldown_minutes = 0 }
    }
  }
} catch { }

# --- Invariants & killswitch ---

# KILLSWITCH_OUTPUT_ONLY_V1_BEGIN
# Output-only kill-switch logic (no actions executed).
function Add-KillReason([System.Collections.Generic.List[string]]$lst,[string]$msg){
  try { if($msg){ $lst.Add($msg) | Out-Null } } catch { }
}
function Resolve-TopReason([System.Collections.Generic.List[string]]$violations,[string]$blockgTop){
  try {
    if($violations -and $violations.Count -gt 0){ return [string]$violations[0] }
  } catch { }
  $t = ([string]$blockgTop).Trim()
  if($t){ return $t }
  return "-"
}
# KILLSWITCH_OUTPUT_ONLY_V1_END

$invOk = ($viol.Count -eq 0)
$kill = $false
$killAction = "NONE"
$killReasons = New-Object System.Collections.Generic.List[string]

# LIVE strong invariants
$mc = BoolProp $rc "market_closed_today" $true
$sn = ""; if($rc.PSObject.Properties.Name -contains "session_name"){ $sn = [string]$rc.session_name }

if($runMode -eq "LIVE"){
  if($mc){ $viol.Add("live_disallowed_market_closed_today=true") | Out-Null }
  if(($sem + "") -ne "FULL_LIVE_ELIGIBLE"){ $viol.Add(("live_requires_full_live_eligible sem=" + $sem)) | Out-Null }
  $symReady = $false
  if($sy -eq "NVDA"){ $symReady = $nvReady }
  elseif($sy -eq "SPY"){ $symReady = $spyReady }
  elseif($sy -eq "QQQ"){ $symReady = $qqqReady }
  if(-not $symReady){ $viol.Add(("live_symbol_not_ready symbol=" + $sy)) | Out-Null }
  if([bool]$risk.crisis_regime){ $viol.Add("crisis_regime=true") | Out-Null }
  if([bool]$risk.portfolio_halt){ $viol.Add("portfolio_halt=true") | Out-Null }
  if([bool]$risk.risk_flatten){ $viol.Add("risk_flatten=true") | Out-Null }
}

# killswitch mapping (output-only for now)
# Policy:
# - LIVE: any invariant violation => kill=true (DISARM). Crisis/flatten/portfolio_halt => FLATTEN_AND_DISARM.
# - PAPERLIVE: invariant violation => kill=true (HALT_PAPERLIVE).
# - PAPER: never kill; only report.
$kill = $false
$killAction = "NONE"
$killReasons = New-Object System.Collections.Generic.List[string]

if($runMode -eq "LIVE"){
  if([bool]$risk.crisis_regime -or [bool]$risk.portfolio_halt -or [bool]$risk.risk_flatten){
    $kill = $true
    $killAction = "FLATTEN_AND_DISARM"
    if([bool]$risk.crisis_regime){ Add-KillReason $killReasons "crisis_regime=true" }
    if([bool]$risk.portfolio_halt){ Add-KillReason $killReasons "portfolio_halt=true" }
    if([bool]$risk.risk_flatten){ Add-KillReason $killReasons "risk_flatten=true" }
  }
  if($viol.Count -gt 0){
    $kill = $true
    if($killAction -eq "NONE"){ $killAction = "DISARM" }
    foreach($v in $viol){ Add-KillReason $killReasons $v }
  }
} elseif($runMode -eq "PAPERLIVE"){
  if($viol.Count -gt 0){
    $kill = $true
    $killAction = "HALT_PAPERLIVE"
    foreach($v in $viol){ Add-KillReason $killReasons $v }
  }
} else {
  # PAPER: output-only; no kill
  $kill = $false
  $killAction = "NONE"
}

$payload = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  market = $mk
  symbol = $sy
  run_mode = $runMode

  runcontext = [ordered]@{
    as_of_date = $asOf
    market_closed_today = [bool]$mc
    session_name = $sn
    logs_dir_out = $logsDirOut
  }

  a2 = [ordered]@{
    phase4 = $p4
    phase23 = $p23
    ev_hard = $evh
  }

  blockg = [ordered]@{
    stub_present = [bool]$stubPresent
    contract_semantics_level = $sem
    contract_semantics_reason = $semr
    nvda_blockg_ready = [bool]$nvReady
    spy_blockg_ready  = [bool]$spyReady
    qqq_blockg_ready  = [bool]$qqqReady
    reasons_not_ready_top = $top
  }

  risk = $risk

  invariants = [ordered]@{
    ok = [bool]($viol.Count -eq 0)
    violations = @($viol)
  }

  killswitch = [ordered]@{
    kill = [bool]$kill
    action = $killAction
    reasons = @($killReasons)
  }
}

# Ensure output dir
try {
  $od = Split-Path -Parent $OutPath
  if($od -and -not (Test-Path -LiteralPath $od)){ New-Item -ItemType Directory -Force -Path $od | Out-Null }
} catch { }

Write-Utf8NoBomLf $OutPath (($payload | ConvertTo-Json -Depth 8))

if($EmitConsole){
  $top2 = ($top + "")
  $top2 = Resolve-TopReason $viol $top
  Write-Host ("[DASH] market=" + $mk + " sym=" + $sy + " mode=" + $runMode + " asof=" + $asOf + " closed=" + $mc + " sem=" + $sem + " kill=" + $kill + " top=" + $top2) -ForegroundColor Cyan
}

exit 0
