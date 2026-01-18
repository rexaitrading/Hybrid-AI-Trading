[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","HK_SH","HK_SZ","SG","IN","KR","TW")]
  [string]$Market = "US",

  # Symbol used only for RunContext resolution + regime_status producer (NVDA default)
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if($Text.Length -gt 0 -and $Text[-1] -ne "`n"){ $Text += "`n" }
  [System.IO.File]::WriteAllText($Path,$Text,$utf8)
}

function Slice10([string]$s){
  $s = (($s + "")).Trim()
  if($s.Length -ge 10){ return $s.Substring(0,10) }
  return $s
}

# --- Resolve repo root deterministically ---
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $toolsDir) -ErrorAction Stop).Path
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

# --- RunContext to derive todayLocal + logsDirOut (A3 style) ---
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$rcPath = Join-Path $repoRoot "tools\Resolve-RunContext.ps1"
if(-not (Test-Path -LiteralPath $rcPath)){ throw "[FAIL-CLOSED] missing Resolve-RunContext.ps1: $rcPath" }

$rcRaw = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $rcPath -Market $Market -Symbol $Symbol 2>$null | Out-String
$rcRaw = (($rcRaw + "")).Trim()
$i0 = $rcRaw.IndexOf("{"); $i1 = $rcRaw.LastIndexOf("}")
if($i0 -lt 0 -or $i1 -le $i0){ throw "[FAIL-CLOSED] Resolve-RunContext did not return JSON" }
$rc = ($rcRaw.Substring($i0, ($i1-$i0+1)) | ConvertFrom-Json -ErrorAction Stop)

$todayLocal = Slice10 ([string]$rc.as_of_date)
$logsDirOut = ""
try {
  if($rc.PSObject.Properties.Name -contains "logs_dir_out"){ $logsDirOut = ([string]$rc.logs_dir_out).Trim() }
} catch { $logsDirOut = "" }
if(-not $logsDirOut){
  try {
    if($rc.PSObject.Properties.Name -contains "logs_dir"){ $logsDirOut = ([string]$rc.logs_dir).Trim() }
  } catch { $logsDirOut = "" }
}
if(-not $todayLocal){ throw "[FAIL-CLOSED] todayLocal empty" }
if(-not $logsDirOut){ throw "[FAIL-CLOSED] logsDirOut empty" }
New-Item -ItemType Directory -Force -Path $logsDirOut | Out-Null

# --- Determine run mode (LIVE vs PAPER/PAPERLIVE) ---
$runMode = ((($env:HAT_MODE + "")).Trim().ToUpperInvariant())
if(-not $runMode){ $runMode = "PAPER" }
$isLive = ($runMode -eq "LIVE")

# --- Read regime_status.json (must exist for ok_today) ---
$regimePath = Join-Path $logsDirOut "regime_status.json"
$regime = "NORMAL"
$regimeOkToday = $false
$regimeReason = "missing_regime_status_json"

try {
  if(Test-Path -LiteralPath $regimePath){
    $rj = Get-Content -LiteralPath $regimePath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
    if($rj){
      if($rj.PSObject.Properties.Name -contains "regime"){ $regime = ([string]$rj.regime).ToUpperInvariant() }
      if($rj.PSObject.Properties.Name -contains "regime_ok_today"){ $regimeOkToday = [bool]$rj.regime_ok_today }
      if($rj.PSObject.Properties.Name -contains "regime_reason"){ $regimeReason = [string]$rj.regime_reason }
    }
  }
} catch {
  $regimeOkToday = $false
  $regimeReason = "regime_status_parse_failed"
}

# --- Action policy (deterministic v1) ---
# Outputs are "Notion-friendly" and can be consumed by Python engines later.
# Any LIVE run requires regime_ok_today true, else ok_today=false (fail-closed).
$size_mult = 1.0
$deny_new_trades = $false
$cooldown_minutes = 0
$stop_mult = 1.0
$target_mult = 1.0

$reasons = New-Object System.Collections.Generic.List[string]

# Base: regime must be ok_today for LIVE.
if($isLive -and (-not $regimeOkToday)){
  $reasons.Add("live_failclosed_regime_ok_today=false") | Out-Null
}

switch ($regime) {
  "CRISIS" {
    $deny_new_trades = $true
    $size_mult = 0.0
    $cooldown_minutes = 120
    $stop_mult = 1.0
    $target_mult = 1.0
    $reasons.Add("regime=CRISIS deny_new_trades=true") | Out-Null
  }
  "HIGH_VOL" {
    $deny_new_trades = $false
    $size_mult = 0.35
    $cooldown_minutes = 0
    $stop_mult = 1.40
    $target_mult = 1.20
    $reasons.Add("regime=HIGH_VOL size_mult=0.35 stop_mult=1.40 target_mult=1.20") | Out-Null
  }
  "CHOP" {
    $deny_new_trades = $false
    $size_mult = 0.25
    $cooldown_minutes = 0
    $stop_mult = 1.10
    $target_mult = 0.85
    $reasons.Add("regime=CHOP size_mult=0.25 target_mult=0.85") | Out-Null
  }
  "LOW_LIQUIDITY" {
    $deny_new_trades = $true
    $size_mult = 0.0
    $cooldown_minutes = 30
    $stop_mult = 1.0
    $target_mult = 1.0
    $reasons.Add("regime=LOW_LIQUIDITY deny_new_trades=true") | Out-Null
  }
  default {
    $deny_new_trades = $false
    $size_mult = 1.0
    $cooldown_minutes = 0
    $stop_mult = 1.0
    $target_mult = 1.0
    $reasons.Add("regime=NORMAL") | Out-Null
  }
}

# --- Compose payload ---
$okToday = $true
if($isLive -and (-not $regimeOkToday)){ $okToday = $false }

$payload = [ordered]@{
  schema = "regime_actions.v1"
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  market = $Market
  symbol = $Symbol
  as_of_date = $todayLocal

  ok_today = [bool]$okToday
  regime = $regime
  regime_ok_today = [bool]$regimeOkToday
  regime_reason = $regimeReason
  regime_status_path = $regimePath

  deny_new_trades = [bool]$deny_new_trades
  size_multiplier = [double]$size_mult
  cooldown_minutes = [int]$cooldown_minutes
  stop_multiplier = [double]$stop_mult
  target_multiplier = [double]$target_mult

  reasons = @($reasons)
}

$outPath = Join-Path $logsDirOut "regime_actions.json"
Write-Utf8NoBomLf $outPath ($payload | ConvertTo-Json -Depth 8)

Write-Host ("[REGIME_ACTIONS] wrote " + $outPath + " ok_today=" + $okToday + " regime=" + $regime) -ForegroundColor Green
exit 0
