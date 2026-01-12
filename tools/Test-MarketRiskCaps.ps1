[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ")] [string]$Market="JP",
  [ValidateSet("REQUIRE_ENABLED","ALLOW_DISABLED")] [string]$Mode="REQUIRE_ENABLED"
)

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


# RISKCAP_ENABLED_CHECK_BEGIN
if($Mode -eq "REQUIRE_ENABLED"){
  # Market profile enabled must be true
  $mcfg = Join-Path $repoRoot ("configs\markets\" + $Market + ".json")
  if(-not (Test-Path -LiteralPath $mcfg)){
    Write-Host ("[RISKCAP] FAIL-CLOSED: missing market profile => " + $mcfg) -ForegroundColor Red
    exit 2
  }
  $mj = Get-Content -LiteralPath $mcfg -Raw -Encoding UTF8 | ConvertFrom-Json
  $mEnabled = $false
  try { $mEnabled = [bool]$mj.enabled } catch { $mEnabled = $false }
  if(-not $mEnabled){
    Write-Host ("[RISKCAP] FAIL-CLOSED: market disabled by profile => " + $Market) -ForegroundColor Red
    exit 2
  }

  # Risk cap config enabled must be true
  $rcEnabled = $false
  try { $rcEnabled = [bool]$j.enabled } catch { $rcEnabled = $false }
  if(-not $rcEnabled){
    Write-Host ("[RISKCAP] FAIL-CLOSED: market disabled by risk cap config => " + $Market) -ForegroundColor Red
    exit 2
  }
}
# RISKCAP_ENABLED_CHECK_END
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
