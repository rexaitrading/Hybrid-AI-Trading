[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ","CN_SH","CN_SZ")]
  [string]$Market = "US",

  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL",

  [ValidateSet("PAPER","PAPERLIVE","LIVE")]
  [string]$TradeMode = "PAPER",

  [string]$AsOfDate = ""
)

Set-StrictMode -Version Latest
# A3_REPOROOT_SINGLE_TRUTH_BEGIN
# Single truth for repo_root: if env:HAT_REPO_ROOT is set, we MUST use it verbatim (GetFullPath only).
# No Resolve-Path on env root (prevents mojibake corruption).
$__envRepoRoot = (($env:HAT_REPO_ROOT + "")).Trim()
if($__envRepoRoot){
  $__envRepoRoot = [System.IO.Path]::GetFullPath($__envRepoRoot)
  if(-not (Test-Path -LiteralPath (Join-Path $__envRepoRoot ".git"))){
    throw ("[FAIL-CLOSED] env:HAT_REPO_ROOT invalid (.git missing): " + $__envRepoRoot)
  }
}
# A3_REPOROOT_SINGLE_TRUTH_END

$ErrorActionPreference="Stop"
chcp 65001 | Out-Null
# A3_OUTPUT_ENCODING_BEGIN
try {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $OutputEncoding = $utf8
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding  = $utf8
} catch { }
# A3_OUTPUT_ENCODING_END
# A3_REPOROOT_ENVFIRST_V2_BEGIN
function Resolve-RepoRootEnvFirst(){
  $envRoot = (($env:HAT_REPO_ROOT + "")).Trim()
  if($envRoot){
    try {
      $r = (Resolve-Path -LiteralPath $envRoot -ErrorAction Stop).Path
      if(Test-Path -LiteralPath (Join-Path $r ".git")){ return $r }
    } catch { }
  }
  # fallback to script-based resolver
  return (Resolve-RepoRoot)
}

function CanonPath([string]$p){
  try { return (Resolve-Path -LiteralPath $p -ErrorAction Stop).Path } catch { return $p }
}
# A3_REPOROOT_ENVFIRST_V2_END
function Resolve-RepoRoot(){
  $toolsDir = Split-Path -Parent $PSCommandPath
  $rr = Split-Path -Parent $toolsDir
  try { return (Resolve-Path -LiteralPath $rr -ErrorAction Stop).Path } catch { return $rr }
}

# --- ENV OVERRIDES (A3 single-truth; only when params not explicitly provided) ---
# Market
if(-not $PSBoundParameters.ContainsKey("Market")){
  $mEnv = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant()
  if($mEnv){
    if($mEnv -notin @("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ","CN_SH","CN_SZ")){
      throw ("[FAIL-CLOSED] invalid HAT_MARKET=" + $mEnv)
    }
    $Market = $mEnv
  }
}

# Symbol
if(-not $PSBoundParameters.ContainsKey("Symbol")){
  $sEnv = (($env:HAT_SYMBOL + "")).Trim().ToUpperInvariant()
  if($sEnv){
    if($sEnv -notin @("NVDA","SPY","QQQ","ALL")){
      throw ("[FAIL-CLOSED] invalid HAT_SYMBOL=" + $sEnv)
    }
    $Symbol = $sEnv
  }
}

# TradeMode (accept HAT_TRADE_MODE first, then HAT_MODE)
if(-not $PSBoundParameters.ContainsKey("TradeMode")){
  $tmEnv = (($env:HAT_TRADE_MODE + "")).Trim().ToUpperInvariant()
  if(-not $tmEnv){ $tmEnv = (($env:HAT_MODE + "")).Trim().ToUpperInvariant() }
  if($tmEnv){
    if($tmEnv -notin @("PAPER","PAPERLIVE","LIVE")){
      throw ("[FAIL-CLOSED] invalid HAT_TRADE_MODE/HAT_MODE=" + $tmEnv)
    }
    $TradeMode = $tmEnv
  }
}
# --- END ENV OVERRIDES ---

# --- Stock Connect market ID normalization (no engine constraints) ---
$marketIn = ($Market + "").Trim().ToUpperInvariant()
switch($marketIn){
  "CN_SH" { $Market = "HK_SH" }
  "CN_SZ" { $Market = "HK_SZ" }
  default { }
}
# --- end normalization ---

# A3_REPOROOT_ENVFIRST_BEGIN
# Canonical repo root: prefer env:HAT_REPO_ROOT when it points to a real repo (prevents mojibake path bleed).
function Resolve-RepoRootEnvFirst(){
  $envRoot = (($env:HAT_REPO_ROOT + "")).Trim()
  if($envRoot){
    try {
      $r = (Resolve-Path -LiteralPath $envRoot -ErrorAction Stop).Path
      if(Test-Path -LiteralPath (Join-Path $r ".git")){ return $r }
    } catch { }
  }
  return (Resolve-RepoRoot)
}
# A3_REPOROOT_ENVFIRST_END
# A3_REPOROOT_FS_TRUTH_BEGIN
# Single truth: prefer env:HAT_REPO_ROOT when it is a real repo (prevents mojibake repo_root).
# A3_FS_TRUTH_REPOROOT_BEGIN
# FS-truth: prefer env:HAT_REPO_ROOT WITHOUT Resolve-Path (prevents mojibake path corruption).
function Get-RepoRootFsTruth(){
  $envRoot = (($env:HAT_REPO_ROOT + "")).Trim()
  if($envRoot){
    $r = [System.IO.Path]::GetFullPath($envRoot)
    if(-not (Test-Path -LiteralPath (Join-Path $r ".git"))){
      throw ("[FAIL-CLOSED] env:HAT_REPO_ROOT invalid (.git missing): " + $r)
    }
    return $r
  }
  $r2 = (Resolve-RepoRoot)
  return [System.IO.Path]::GetFullPath($r2)
}
# A3_FS_TRUTH_REPOROOT_END
# A3_REPOROOT_ASSIGN_FIX_BEGIN
$repoRoot = ""
if($__envRepoRoot){
  $repoRoot = $__envRepoRoot
} else {
  $repoRoot = Resolve-RepoRoot
  $repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
}
# A3_REPOROOT_ASSIGN_FIX_END
if($repoRoot){
# [A3] disabled secondary repoRoot assignment: $repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
  if(-not (Test-Path -LiteralPath (Join-Path $repoRoot ".git"))){
    throw ("[FAIL-CLOSED] env:HAT_REPO_ROOT is not a repo (.git missing): " + $repoRoot)
  }
} else {
# [A3] disabled secondary repoRoot assignment: $repoRoot = Resolve-RepoRoot
# [A3] disabled secondary repoRoot assignment: $repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
}
# A3_REPOROOT_FS_TRUTH_END
# [A3] disabled secondary repoRoot assignment: $repoRoot = Resolve-RepoRootEnvFirst
# A3_REPOROOT_CANON_BEGIN
# [A3] disabled secondary repoRoot assignment: $repoRoot = CanonPath $repoRoot
# A3_REPOROOT_CANON_END
if(-not $TradeMode){
  $TradeMode = (($env:HAT_MODE + "")).Trim().ToUpperInvariant()
  if(-not $TradeMode){ $TradeMode = "PAPER" }
}
if($TradeMode -notin @("PAPER","PAPERLIVE","LIVE")){ $TradeMode = "PAPER" }
$isPaper = ($TradeMode -ne "LIVE")

# MarketContext is authoritative for session/calendar/day truth
$mcPath = Join-Path $repoRoot "tools\Resolve-MarketContext.ps1"
if(-not (Test-Path -LiteralPath $mcPath)){ throw "Missing Resolve-MarketContext.ps1" }

$mcArgs = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$mcPath,"-Market",$Market)
if((($AsOfDate + "")).Trim()){
  $mcArgs += @("-AsOfDate",$AsOfDate)
}

$mcRaw = & powershell @mcArgs 2>$null | Out-String
$mcRaw = ($mcRaw + "").Trim()
if(-not $mcRaw){ throw "Resolve-MarketContext returned empty stdout" }

# If any stray text exists, keep only JSON payload from first '{' to last '}'
$ix0 = $mcRaw.IndexOf('{')
$ix1 = $mcRaw.LastIndexOf('}')
if($ix0 -lt 0 -or $ix1 -le $ix0){
  throw ("Resolve-MarketContext did not return JSON. Head=" + ($mcRaw.Substring(0,[Math]::Min(120,$mcRaw.Length))))
}
$mcJson = $mcRaw.Substring($ix0, ($ix1 - $ix0 + 1))
$mc = $mcJson | ConvertFrom-Json -ErrorAction Stop
if(-not $mc){ throw "Resolve-MarketContext returned empty" }

# Per-market logs dir (A3 FS-truth canonical; avoid mojibake)
$mk2 = ($Market + "").Trim().ToUpperInvariant()
if(-not $mk2){ $mk2 = "US" }
$logsDirOut = Join-Path (Join-Path $repoRoot "logs") $mk2
New-Item -ItemType Directory -Force -Path $logsDirOut | Out-Null
# A3_LOGSDIR_FULLPATH_GUARD_BEGIN
$logsDirOut = [System.IO.Path]::GetFullPath($logsDirOut)
# A3_LOGSDIR_FULLPATH_GUARD_END
# A3_FS_TRUTH_LOGSDIR_BEGIN
$logsDirOut = [System.IO.Path]::GetFullPath($logsDirOut)
# A3_FS_TRUTH_LOGSDIR_END
# A3_LOGSDIR_CANON_BEGIN
$logsDirOut = CanonPath $logsDirOut
# A3_LOGSDIR_CANON_END
# Output: keep BOTH logs_dir and logs_dir_out for compatibility
# A3_REPOROOT_PROOF_GUARD_BEGIN
# If env root exists, emitted repo_root MUST equal it (hard proof guard).
try {
  if($__envRepoRoot){
    if(([string]$repoRoot) -ne ([string]$__envRepoRoot)){
      throw ("[FAIL-CLOSED] repo_root != env:HAT_REPO_ROOT. repo_root=" + $repoRoot + " env=" + $__envRepoRoot)
    }
  }
} catch { throw }
# A3_REPOROOT_PROOF_GUARD_END
[pscustomobject]@{
  repo_root = $repoRoot

  trade_mode = $TradeMode
  mode = $TradeMode
  is_paper = [bool]$isPaper

  symbol = $Symbol
  market = $Market
  broker_profile = (($env:HAT_BROKER_PROFILE + "")).Trim()

  calendar_id = $mc.calendar_id
  market_tz = $mc.tz
  market_tz_resolved_id = $mc.tz_resolved_id

  as_of_date = $mc.as_of_date
  as_of_date_source = $mc.as_of_date_source
  now_utc = $mc.now_utc
  now_local = $mc.now_local

  market_closed_today = [bool]$mc.market_closed_today
  market_closed_reason = $mc.market_closed_reason
  is_open_now = [bool]$mc.is_open_now
  session_name = $mc.session_name
  session = $mc.session_name
  is_trading_day = [bool]$mc.is_trading_day

  logs_dir_out = $logsDirOut
  logs_dir = $logsDirOut
} | ConvertTo-Json -Depth 6
