[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol="NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$today = (Get-Date).ToString("yyyy-MM-dd")
$dow   = (Get-Date).DayOfWeek.ToString()

Write-Host ("[INPUTS] NOW={0} {1} Symbol={2}" -f $today,$dow,$Symbol) -ForegroundColor Cyan

# Weekend/holiday friendly: do not THROW; report + fail-closed exit=2.
$fail = $false

# EV evidence
$evPath = ".\logs\ev_hard_evidence_raw.json"
if(-not (Test-Path $evPath)){
  Write-Host "[INPUTS] EV evidence missing: logs\ev_hard_evidence_raw.json" -ForegroundColor Yellow
  $fail = $true
} else {
  $ev = Get-Content $evPath -Raw -Encoding utf8 | ConvertFrom-Json
  $evAsOf = (($ev.as_of_date + "") + "          ").Substring(0,10)
  Write-Host ("[INPUTS] EV as_of_date={0} ok={1}" -f $evAsOf,$ev.ok) -ForegroundColor Yellow
  if($evAsOf -ne $today){
    Write-Host ("[INPUTS] EV STALE vs today={0} (expected on weekends)" -f $today) -ForegroundColor Yellow
    $fail = $true
  }
}

# GateScore daily summary row (strict today)
$gs = ".\logs\gatescore_daily_summary.csv"
if(-not (Test-Path $gs)){
  Write-Host "[INPUTS] GateScore daily summary missing: logs\gatescore_daily_summary.csv" -ForegroundColor Yellow
  $fail = $true
} else {
  $has = Select-String -Path $gs -Pattern ("^" + [regex]::Escape($today) + "," + [regex]::Escape($Symbol) + ",") -Quiet
  Write-Host ("[INPUTS] GateScore today row present={0}" -f $has) -ForegroundColor Yellow
  if(-not $has){
    Write-Host "[INPUTS] GateScore not fresh for today (expected on weekends)" -ForegroundColor Yellow
    $fail = $true
  }
}

if($fail){
  Write-Host "[INPUTS] FAIL-CLOSED (not suitable to arm live today)." -ForegroundColor Yellow
  exit 2
}

Write-Host "[INPUTS] OK (inputs look fresh for today)." -ForegroundColor Green
exit 0