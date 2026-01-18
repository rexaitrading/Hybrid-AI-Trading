[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",

  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [ValidateSet("PAPER","PAPERLIVE","LIVE")]
  [string]$Mode = "PAPERLIVE",

  [switch]$NoConsole
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

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
  if(-not $NoConsole){ Write-Host ("[FAIL-CLOSED] " + $m) -ForegroundColor Red }
  exit 2
}

function Slice10([string]$d){
  $s = ([string]$d).Trim()
  if($s.Length -ge 10){ return $s.Substring(0,10) }
  return $s
}

function Read-JsonFromStdout([string]$raw){
  $r = (($raw + "")).Trim()
  $i0 = $r.IndexOf('{'); $i1 = $r.LastIndexOf('}')
  if($i0 -lt 0 -or $i1 -le $i0){ return $null }
  try { return ($r.Substring($i0, ($i1-$i0+1)) | ConvertFrom-Json -ErrorAction Stop) } catch { return $null }
}

function Read-JsonFile([string]$Path){
  try {
    if(-not (Test-Path -LiteralPath $Path)){ return $null }
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if(-not $raw){ return $null }
    return ($raw | ConvertFrom-Json -ErrorAction Stop)
  } catch { return $null }
}

$mk = (($Market + "")).Trim().ToUpperInvariant()
$sy = (($Symbol + "")).Trim().ToUpperInvariant()
$rm = (($Mode + "")).Trim().ToUpperInvariant()
if($rm -notin @("PAPER","PAPERLIVE","LIVE")){ Fail ("invalid -Mode=" + $Mode) }

# Policy A: non-US markets only support NVDA
if($mk -ne "US" -and $sy -in @("SPY","QQQ")){
  Fail ("PolicyA symbol_not_applicable_for_market market=" + $mk + " symbol=" + $sy)
}

# Repo root
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
try { $repoRoot = (Resolve-Path -LiteralPath $repoRoot -ErrorAction Stop).Path } catch { }
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

# Required tools
$rcPath   = Join-Path $toolsDir "Resolve-RunContext.ps1"
$dashPath = Join-Path $toolsDir "Build-OpsDashboard.ps1"
$ksPath   = Join-Path $toolsDir "Write-KillSwitchStatus.ps1"
$invPath  = Join-Path $toolsDir "Write-InvariantsStatus.ps1"

foreach($p in @($rcPath,$dashPath,$ksPath,$invPath)){
  if(-not (Test-Path -LiteralPath $p)){ Fail ("missing tool: " + $p) }
}

# Resolve RunContext
$rcRaw = (& $rcPath -Market $mk -Symbol $sy 2>&1 | Out-String)
$rcObj = Read-JsonFromStdout $rcRaw
if(-not $rcObj){ Fail ("Resolve-RunContext did not return JSON market=" + $mk) }

if(-not ($rcObj.PSObject.Properties.Name -contains "logs_dir_out")){ Fail "RunContext missing logs_dir_out" }
if(-not ($rcObj.PSObject.Properties.Name -contains "as_of_date")){ Fail "RunContext missing as_of_date" }

$logsDirOut = ([string]$rcObj.logs_dir_out).Trim()
if(-not $logsDirOut){ Fail "RunContext logs_dir_out empty" }
if(-not (Test-Path -LiteralPath $logsDirOut)){ New-Item -ItemType Directory -Force -Path $logsDirOut | Out-Null }

$asOf = Slice10 ([string]$rcObj.as_of_date)

# Set env context (single truth)
$env:HAT_MODE      = $rm
$env:HAT_MARKET    = $mk
$env:HAT_SYMBOL    = $sy
$env:HAT_ASOF_DATE = $asOf
$env:HAT_LOGS_DIR  = $logsDirOut

# Paths
$dashOut = Join-Path $logsDirOut "ops_dashboard.json"
$ksOut   = Join-Path $logsDirOut "killswitch_status.json"
$invOut  = Join-Path $logsDirOut "invariants_status.json"
$outPath = Join-Path $logsDirOut "ops_ready_status.json"

# Run producers deterministically (always attempt)
$steps = @()
$stepFail = $false

function Run-Step([string]$name,[scriptblock]$sb,[switch]$IgnoreFailure){
  $ts0 = (Get-Date).ToUniversalTime().ToString("o")
  $exit = 0
  $err = ""
  try {
    & $sb
    if($LASTEXITCODE -ne $null -and [int]$LASTEXITCODE -ne 0){ $exit = [int]$LASTEXITCODE }
  } catch {
    $exit = 2
    $err = $_.Exception.Message
  }
  $ts1 = (Get-Date).ToUniversalTime().ToString("o")
  $script:steps += [pscustomobject]@{
    name = $name
    ts_utc_start = $ts0
    ts_utc_end = $ts1
    exit_code = $exit
    error = $err
  }
  if($exit -ne 0 -and (-not $IgnoreFailure)){ $script:stepFail = $true }
  if(-not $NoConsole){
    $c = if($exit -eq 0){ "Green" } else { "Red" }
    Write-Host ("[OPSREADY] step=" + $name + " exit=" + $exit + " err=" + $err) -ForegroundColor $c
  }
}

Run-Step "ops_dashboard" { & $dashPath -Market $mk -Symbol $sy -Mode $rm -OutPath $dashOut -EmitConsole:(-not $NoConsole) | Out-Null }
# policy outcomes can exit 2 without breaking producer success
Run-Step "killswitch_status" { & $ksPath -Market $mk -Symbol $sy -Mode $rm -NoConsole:$NoConsole | Out-Null } -IgnoreFailure
Run-Step "invariants_status" { & $invPath -Market $mk -Symbol $sy -Mode $rm -NoConsole:$NoConsole | Out-Null } -IgnoreFailure
# Slippage attribution (execution evidence rollup)
$slipTool = Join-Path $toolsDir "Build-SlippageAttributionDaily.ps1"
$slipIn   = Join-Path $logsDirOut "execution\slippage_events.jsonl"
$slipOutJ = Join-Path $logsDirOut "execution\slippage_attrib_daily.json"
$slipOutC = Join-Path $logsDirOut "execution\slippage_attrib_daily.csv"

$ignoreSlipAttr = $true
# PAPERLIVE/LIVE: if we have at least 1 slippage line, attribution must succeed
if($rm -in @("PAPERLIVE","LIVE")){
  try {
    if(Test-Path -LiteralPath $slipIn){
      $c2 = (Get-Content -LiteralPath $slipIn -Encoding UTF8 | Measure-Object).Count
      if($c2 -gt 0){ $ignoreSlipAttr = $false }
    }
  } catch { }
}

if(Test-Path -LiteralPath $slipTool){
  Run-Step "slippage_attrib" {
    & $slipTool -InPath $slipIn -OutJson $slipOutJ -OutCsv $slipOutC -NoConsole | Out-Null
  } -IgnoreFailure:$ignoreSlipAttr
} else {
  # If tool missing, only fatal when not ignoring and in PAPERLIVE/LIVE with slippage samples
  if(-not $ignoreSlipAttr){
    $script:steps += [pscustomobject]@{
      name="slippage_attrib"
      ts_utc_start=(Get-Date).ToUniversalTime().ToString("o")
      ts_utc_end=(Get-Date).ToUniversalTime().ToString("o")
      exit_code=2
      error="missing Build-SlippageAttributionDaily.ps1"
    }
    $stepFail = $true
  }
}

# Read artifacts
$dash = Read-JsonFile $dashOut
$ks   = Read-JsonFile $ksOut
$inv  = Read-JsonFile $invOut

# Derive fields (mode-aware, fail-closed)
$deny = @()
$kill = $true
$top  = "missing_ops_dashboard"
$tradeAllowed = $false
$ibgFreshOk = $false

$invOk = $false
$invReason = "missing_invariants"
$invViol = @()

if($dash){
  # killswitch fields exist in dashboard as well, but we prefer killswitch_status.json if present
  if($dash.PSObject.Properties.Name -contains "killswitch"){
    try {
      $k = $dash.killswitch
      if($k -and ($k.PSObject.Properties.Name -contains "kill")){
        $kill = [bool]$k.kill
      }
      if($k -and ($k.PSObject.Properties.Name -contains "top_reason")){
        $top = [string]$k.top_reason
      } elseif($k -and ($k.PSObject.Properties.Name -contains "top")){
        $top = [string]$k.top
      }
    } catch { }
  } else {
    # fallback: dashboard sometimes prints top in console only; keep defaults
    $kill = $true
    $top  = "killswitch_missing_in_dashboard"
  }

  # IB evidence
  if($dash.PSObject.Properties.Name -contains "ib"){
    try {
      $ib = $dash.ib
      if($ib -and ($ib.PSObject.Properties.Name -contains "connected")){
        $ibgFreshOk = [bool]$ib.connected
      }
    } catch { }
  }
} else {
  $deny += "missing_ops_dashboard_json"
}

if($ks){
  try {
    if($ks.PSObject.Properties.Name -contains "kill"){ $kill = [bool]$ks.kill }
    if($ks.PSObject.Properties.Name -contains "top_reason"){ $top = [string]$ks.top_reason }
  } catch { }
} else {
  $deny += "missing_killswitch_status"
}

if($inv){
  try {
    if($inv.PSObject.Properties.Name -contains "ok"){ $invOk = [bool]$inv.ok }
    if($inv.PSObject.Properties.Name -contains "reason"){ $invReason = [string]$inv.reason }
    if($inv.PSObject.Properties.Name -contains "violations"){ $invViol = @($inv.violations) }
  } catch { }
} else {
  $deny += "missing_invariants_status"
}

$tradeAllowed = (-not $kill)

# Mode-aware ops_ready:
# - LIVE: fail-closed strict: must have dashboard+killswitch+invariants present, ib fresh ok, tradeAllowed true, invOk true, and producer steps (ops_dashboard) succeeded
# - PAPERLIVE: require dashboard present, killswitch present, ib fresh ok, and tradeAllowed true (invariants can be false but will deny trade anyway via tradeAllowed/invOk)
# - PAPER: always ops_ready true if producer steps succeeded; trade_allowed can still be computed
$opsReady = $false

if($rm -eq "PAPER"){
  $opsReady = (-not $stepFail)
} elseif($rm -eq "PAPERLIVE"){
  if(-not $dash){ $deny += "paperlive_missing_dashboard" }
  if(-not $ks){ $deny += "paperlive_missing_killswitch" }
  if(-not $ibgFreshOk){ $deny += "paperlive_ib_not_fresh" }
  if($kill){ $deny += ("paperlive_kill_top=" + $top) }
  $opsReady = ((-not $stepFail) -and $ibgFreshOk -and (-not $kill) -and $dash -and $ks)
} else {
  # LIVE strict
  if(-not $dash){ $deny += "live_missing_dashboard" }
  if(-not $ks){ $deny += "live_missing_killswitch" }
  if(-not $inv){ $deny += "live_missing_invariants" }
  if(-not $ibgFreshOk){ $deny += "live_ib_not_fresh" }
  if(-not $invOk){ $deny += ("live_invariants_fail reason=" + $invReason) }
  if($kill){ $deny += ("live_kill_top=" + $top) }
  $opsReady = ((-not $stepFail) -and $ibgFreshOk -and (-not $kill) -and $invOk -and $dash -and $ks -and $inv)
}

# Build unified artifact (always emitted)
$artifact = [pscustomobject]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  market = $mk
  symbol = $sy
  run_mode = $rm
  as_of_date = $asOf
  logs_dir_out = $logsDirOut

  ops_ready = $opsReady
  trade_allowed = $tradeAllowed

  kill = $kill
  top_reason = $top

  ibg_fresh_ok = $ibgFreshOk

  invariants_ok = $invOk
  invariants_reason = $invReason
  invariants_violations = @($invViol)

  deny_reasons = @($deny)

  paths = [pscustomobject]@{
    ops_dashboard = $dashOut
    killswitch_status = $ksOut
    invariants_status = $invOut
    ops_ready_status = $outPath
  }

  steps = @($steps)
}

Write-Utf8NoBomLf $outPath ($artifact | ConvertTo-Json -Depth 10)

if(-not $NoConsole){
  $c = if($opsReady){ "Green" } else { "Red" }
  Write-Host ("[OPSREADY] wrote " + $outPath + " ops_ready=" + $opsReady + " trade_allowed=" + $tradeAllowed + " mode=" + $rm) -ForegroundColor $c
}

if($opsReady){ exit 0 }
exit 2
