[CmdletBinding()]
param([ValidateSet("US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ")] [string]$Market="JP")

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$p = Join-Path $repoRoot ("configs\risk_caps\" + $Market + ".json")

if(-not (Test-Path -LiteralPath $p)){
  Write-Host ("[RISKCAP] FAIL-CLOSED: missing risk cap config => " + $p) -ForegroundColor Red
  exit 2
}

$j = Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json

foreach($k in @("daily_loss_cap_usd","max_notional_usd","max_orders_per_day","cooldown_minutes_after_loss_hit")){
  if(-not ($j.PSObject.Properties.Name -contains $k)){
    Write-Host ("[RISKCAP] FAIL-CLOSED: missing field => " + $k) -ForegroundColor Red
    exit 2
  }
}

# basic sanity
if([double]$j.daily_loss_cap_usd -le 0){ exit 2 }
if([double]$j.max_notional_usd -le 0){ exit 2 }
if([int]$j.max_orders_per_day -le 0){ exit 2 }
if([int]$j.cooldown_minutes_after_loss_hit -lt 0){ exit 2 }

Write-Host ("[RISKCAP] OK: Market=" + $Market + " daily_loss_cap_usd=" + $j.daily_loss_cap_usd) -ForegroundColor Green
exit 0
