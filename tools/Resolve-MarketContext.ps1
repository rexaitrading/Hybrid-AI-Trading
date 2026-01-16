[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ","CN_SH","CN_SZ")]
  [string]$Market = "US",
  [string]$AsOfDate = ""
)

# --- Stock Connect market ID normalization (no engine constraints) ---
$marketIn = ($Market + "").Trim().ToUpperInvariant()
switch($marketIn){
  "CN_SH" { $Market = "HK_SH" }
  "CN_SZ" { $Market = "HK_SZ" }
  default { }
}
# --- end normalization ---


Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$cfg = Join-Path $repoRoot ("configs\markets\" + $Market + ".json")
if(-not (Test-Path -LiteralPath $cfg)){ throw "Missing market config: $cfg" }

$j = Get-Content -LiteralPath $cfg -Raw -Encoding UTF8 | ConvertFrom-Json
$tzRaw = [string]$j.tz
$cal = [string]$j.calendar_id

function Resolve-TimeZoneInfo([string]$tzId){
  # Accept Windows tz ids; if config stores IANA ids, map a minimal subset.
  $map = @{
    "America/New_York" = "Eastern Standard Time"
    "America/Chicago"  = "Central Standard Time"
    "America/Los_Angeles" = "Pacific Standard Time"
    "Asia/Tokyo" = "Tokyo Standard Time"
    "Asia/Hong_Kong" = "China Standard Time"
    "Asia/Taipei" = "Taipei Standard Time"
    "Asia/Singapore" = "Singapore Standard Time"
    "Asia/Shanghai"  = "China Standard Time"
    "UTC" = "UTC"
  }

  $candidate = ($tzId + "").Trim()
  if(-not $candidate){ $candidate = "UTC" }

  try { return [System.TimeZoneInfo]::FindSystemTimeZoneById($candidate) } catch { }

  if($map.ContainsKey($candidate)){
    try { return [System.TimeZoneInfo]::FindSystemTimeZoneById($map[$candidate]) } catch { }
  }

  # Last resort: fail-closed to UTC
  return [System.TimeZoneInfo]::Utc
}

function Parse-HHMM([string]$hhmm){
  if(-not $hhmm){ return $null }
  $t = $hhmm.Trim()
  return [TimeSpan]::ParseExact($t, "hh\:mm", $null)
}

function LocalDateTime([string]$ymd, [TimeSpan]$ts){
  return [datetime]::ParseExact($ymd, "yyyy-MM-dd", $null).Add($ts)
}

$tzi = Resolve-TimeZoneInfo $tzRaw
$tzResolvedId = $tzi.Id

# AsOfDate default: today in market tz (best-effort; fallback to local date)
$asOfSource = "param"
if(-not $AsOfDate){
  $asOfSource = "market_tz_now"
  try {
    $nowUtc0 = [DateTimeOffset]::UtcNow
    $local0 = [System.TimeZoneInfo]::ConvertTime($nowUtc0.UtcDateTime, $tzi)
    $AsOfDate = $local0.ToString("yyyy-MM-dd")
  } catch {
    $AsOfDate = (Get-Date).ToString("yyyy-MM-dd")
    $asOfSource = "local_fallback"
  }
}

# Base closed-day logic: weekend
$dt = [DateTime]::ParseExact($AsOfDate,"yyyy-MM-dd",$null)
$closed = ($dt.DayOfWeek -eq "Saturday" -or $dt.DayOfWeek -eq "Sunday")
$closed_reason = if($closed){"weekend"}else{""}

# Per-market holiday override (configs\market_holidays.json) — authoritative
try {
  $holPath = Join-Path $repoRoot "configs\market_holidays.json"
  if(Test-Path -LiteralPath $holPath){
    $hj = Get-Content -LiteralPath $holPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $m = ($Market + "").ToUpperInvariant()

    $dates = @()
    if($hj.PSObject.Properties.Name -contains $m){
      $obj = $hj.$m
      if($obj -and ($obj.PSObject.Properties.Name -contains "closed_dates")){
        $dates = @($obj.closed_dates)
      }
    } elseif($hj.PSObject.Properties.Name -contains "closed_dates") {
      # Back-compat: top-level applies to US only
      if($m -eq "US"){ $dates = @($hj.closed_dates) }
    }

    if($dates -contains $AsOfDate){
      $closed = $true
      $closed_reason = "holiday"
    }
  }
} catch { }

# Session windows (from market profile json)
$rthOpen = ""
$rthClose = ""
$lunchStart = ""
$lunchEnd = ""
try {
  if($j.PSObject.Properties.Name -contains "rth_open_local"){ $rthOpen = [string]$j.rth_open_local }
  if($j.PSObject.Properties.Name -contains "rth_close_local"){ $rthClose = [string]$j.rth_close_local }
  if($j.PSObject.Properties.Name -contains "lunch_break" -and $null -ne $j.lunch_break){
    if($j.lunch_break.PSObject.Properties.Name -contains "start"){ $lunchStart = [string]$j.lunch_break.start }
    if($j.lunch_break.PSObject.Properties.Name -contains "end"){ $lunchEnd = [string]$j.lunch_break.end }
  }
} catch { }

# Intraday open/closed
$nowUtcIso = [DateTimeOffset]::UtcNow.UtcDateTime.ToString("o")
$nowLocalIso = ""
$inRth = $false
$inLunch = $false
$isOpenNow = $false

# NEW: trading day + session label (authoritative)
$isTradingDay = (-not $closed)
$sessionName = "CLOSED"

try {
  $nowUtc = [DateTimeOffset]::UtcNow
  $nowLocal = [System.TimeZoneInfo]::ConvertTime($nowUtc.UtcDateTime, $tzi)
  $nowLocalIso = $nowLocal.ToString("o")

  if(-not $closed){
    $o = Parse-HHMM $rthOpen
    $c = Parse-HHMM $rthClose

    if($o -and $c){
      $startDt = LocalDateTime $AsOfDate $o
      $endDt   = LocalDateTime $AsOfDate $c
      $inRth = ($nowLocal -ge $startDt -and $nowLocal -lt $endDt)

      $ls = Parse-HHMM $lunchStart
      $le = Parse-HHMM $lunchEnd
      if($ls -and $le){
        $lsDt = LocalDateTime $AsOfDate $ls
        $leDt = LocalDateTime $AsOfDate $le
        if($nowLocal -ge $lsDt -and $nowLocal -lt $leDt){ $inLunch = $true }
      }

      $isOpenNow = ($inRth -and -not $inLunch)

      # Session label
      if($nowLocal -lt $startDt){
        $sessionName = "PRE_OPEN"
      } elseif($nowLocal -ge $endDt){
        $sessionName = "AFTER_CLOSE"
      } else {
        if($inLunch){
          $sessionName = "LUNCH_BREAK"
        } elseif($isOpenNow){
          $sessionName = "RTH"
        } else {
          $sessionName = "RTH_CLOSED"
        }
      }
    } else {
      # No valid RTH window => fail-closed
      $isTradingDay = $false
      $isOpenNow = $false
      $sessionName = "CLOSED"
    }
  } else {
    $isOpenNow = $false
    $sessionName = "CLOSED"
  }
} catch {
  # fail-closed
  $closed = $true
  if(-not $closed_reason){ $closed_reason = "error" }
  $isTradingDay = $false
  $inRth = $false
  $inLunch = $false
  $isOpenNow = $false
  $sessionName = "CLOSED"
}

[pscustomobject]@{
  market = $Market
  tz = $tzRaw
  tz_resolved_id = $tzResolvedId
  calendar_id = $cal
  as_of_date = $AsOfDate
  as_of_date_source = $asOfSource

  market_closed_today = [bool]$closed
  market_closed_reason = $closed_reason

  is_trading_day = [bool]$isTradingDay
  session_name = $sessionName

  rth_open_local = $rthOpen
  rth_close_local = $rthClose
  lunch_start_local = $lunchStart
  lunch_end_local = $lunchEnd

  now_utc = $nowUtcIso
  now_local = $nowLocalIso
  in_rth = [bool]$inRth
  in_lunch = [bool]$inLunch
  is_open_now = [bool]$isOpenNow
} | ConvertTo-Json -Depth 6
