[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ")]
  [string]$Market = "US",
  [ValidateSet("PAPER","PAPERLIVE","LIVE")]
  [string]$TradeMode = "PAPER",
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL",
  [string]$AsOfDate = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

if(-not $TradeMode){
  $TradeMode = (($env:HAT_MODE + "")).Trim().ToUpperInvariant()
  if(-not $TradeMode){ $TradeMode = "PAPER" }
}
if($TradeMode -notin @("PAPER","PAPERLIVE","LIVE")){ $TradeMode = "PAPER" }

$isPaper = ($TradeMode -ne "LIVE")

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
if($ix0 -lt 0 -or $ix1 -le $ix0){ throw ("Resolve-MarketContext did not return JSON. Head=" + ($mcRaw.Substring(0,[Math]::Min(80,$mcRaw.Length)))) }
$mcJson = $mcRaw.Substring($ix0, ($ix1 - $ix0 + 1))

$mc = $mcJson | ConvertFrom-Json -ErrorAction Stop
if(-not $mc){ throw "Resolve-MarketContext returned empty" }

$lmPath = Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1"
$logsDirOut = $null
try { $logsDirOut = & powershell -NoProfile -ExecutionPolicy Bypass -File $lmPath -Market $Market } catch { $logsDirOut = $null }
if(-not $logsDirOut){ $logsDirOut = Join-Path $repoRoot "logs" }

[pscustomobject]@{
  repo_root = $repoRoot
  trade_mode = $TradeMode
  is_paper = [bool]$isPaper
  symbol = $Symbol

  market = $Market
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
  is_trading_day = [bool]$mc.is_trading_day

  logs_dir_out = $logsDirOut
} | ConvertTo-Json -Depth 6
