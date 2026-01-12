[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ")]
  [string]$Market = "US",
  [string]$AsOfDate = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$cfg = Join-Path $repoRoot ("configs\markets\" + $Market + ".json")
if(-not (Test-Path -LiteralPath $cfg)){ throw "Missing market config: $cfg" }

$j = Get-Content -LiteralPath $cfg -Raw -Encoding UTF8 | ConvertFrom-Json
$tz = [string]$j.tz
$cal = [string]$j.calendar_id

function Parse-HHMM([string]$hhmm){
  if(-not $hhmm){ return $null }
  $t = $hhmm.Trim()
  return [TimeSpan]::ParseExact($t, "hh\:mm", $null)
}
function LocalDateTime([string]$ymd, [TimeSpan]$ts){
  return [datetime]::ParseExact($ymd, "yyyy-MM-dd", $null).Add($ts)
}

# AsOfDate default: today in market tz (best-effort; fallback to local date)
if(-not $AsOfDate){
  try {
    $nowUtc = [DateTimeOffset]::UtcNow
    $tzi = [System.TimeZoneInfo]::FindSystemTimeZoneById($tz)
    $local = [System.TimeZoneInfo]::ConvertTime($nowUtc.UtcDateTime, $tzi)
    $AsOfDate = $local.ToString("yyyy-MM-dd")
  } catch {
    $AsOfDate = (Get-Date).ToString("yyyy-MM-dd")
  }
}

# Placeholder closed-day logic (Phase 5 Step1): weekend-only rule
# Later: replace with true exchange calendar per Market/calendar_id
$dt = [DateTime]::ParseExact($AsOfDate,"yyyy-MM-dd",$null)
$closed = ($dt.DayOfWeek -eq "Saturday" -or $dt.DayOfWeek -eq "Sunday")

# Per-market holiday override (configs\market_holidays.json)
try {
  $holPath = Join-Path $repoRoot "configs\market_holidays.json"
  if(Test-Path -LiteralPath $holPath){
    $hj = Get-Content -LiteralPath $holPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $m = ($Market + "").ToUpperInvariant()

    $dates = @()
    if($hj.PSObject.Properties.Name -contains "closed_dates"){
      # Back-compat: old schema treated as US
      if($m -eq "US"){ $dates = @($hj.closed_dates) }
    } elseif($hj.PSObject.Properties.Name -contains $m) {
      $obj = $hj.$m
      if($obj -and ($obj.PSObject.Properties.Name -contains "closed_dates")){
        $dates = @($obj.closed_dates)
      }
    }

    if($dates -contains $AsOfDate){
      $closed = $true
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

# Intraday open/closed (best-effort): requires not closed day AND within RTH and not in lunch
$isOpenNow = $false
try {
  if(-not $closed){
    $nowUtc = [DateTimeOffset]::UtcNow
    $tzi = [System.TimeZoneInfo]::FindSystemTimeZoneById($tz)
    $nowLocal = [System.TimeZoneInfo]::ConvertTime($nowUtc.UtcDateTime, $tzi)

    $o = Parse-HHMM $rthOpen
    $c = Parse-HHMM $rthClose
    if($o -and $c){
      $startDt = LocalDateTime $AsOfDate $o
      $endDt   = LocalDateTime $AsOfDate $c
      $inRth = ($nowLocal -ge $startDt -and $nowLocal -lt $endDt)

      $inLunch = $false
      $ls = Parse-HHMM $lunchStart
      $le = Parse-HHMM $lunchEnd
      if($ls -and $le){
        $lsDt = LocalDateTime $AsOfDate $ls
        $leDt = LocalDateTime $AsOfDate $le
        if($nowLocal -ge $lsDt -and $nowLocal -lt $leDt){ $inLunch = $true }
      }
      $isOpenNow = ($inRth -and -not $inLunch)
    }
  }
} catch { $isOpenNow = $false }
[pscustomobject]@{
  market = $Market
  tz = $tz
  calendar_id = $cal
  as_of_date = $AsOfDate
  market_closed_today = [bool]$closed
  rth_open_local = $rthOpen
  rth_close_local = $rthClose
  lunch_start_local = $lunchStart
  lunch_end_local = $lunchEnd
  is_open_now = [bool]$isOpenNow
} | ConvertTo-Json -Depth 5
