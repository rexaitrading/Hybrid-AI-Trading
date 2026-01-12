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

[pscustomobject]@{
  market = $Market
  tz = $tz
  calendar_id = $cal
  as_of_date = $AsOfDate
  market_closed_today = [bool]$closed
} | ConvertTo-Json -Depth 5

