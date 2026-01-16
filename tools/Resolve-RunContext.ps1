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
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Resolve-RepoRoot(){
  $toolsDir = Split-Path -Parent $PSCommandPath
  $rr = Split-Path -Parent $toolsDir
  try { return (Resolve-Path -LiteralPath $rr -ErrorAction Stop).Path } catch { return $rr }
}

# --- Stock Connect market ID normalization (no engine constraints) ---
$marketIn = ($Market + "").Trim().ToUpperInvariant()
switch($marketIn){
  "CN_SH" { $Market = "HK_SH" }
  "CN_SZ" { $Market = "HK_SZ" }
  default { }
}
# --- end normalization ---

$repoRoot = Resolve-RepoRoot

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

# Output: keep BOTH logs_dir and logs_dir_out for compatibility
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
