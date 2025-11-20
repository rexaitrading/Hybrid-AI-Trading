[CmdletBinding()]
param(
    [string]$ConfigPath = 'config\phase5_risk.json'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptRoot = $PSScriptRoot
$repoRoot   = Split-Path -Parent $scriptRoot

Set-Location $repoRoot

$cfgPath = Join-Path $repoRoot $ConfigPath
if (-not (Test-Path $cfgPath)) {
    throw "Phase5 risk config missing: $cfgPath"
}

$risk = Get-Content $cfgPath -Raw | ConvertFrom-Json

# Export core risk knobs as env vars for Python
$env:PHASE5_DAILY_LOSS_CAP_USD      = [string]$risk.daily_loss_cap_usd
$env:PHASE5_MAX_DRAWDOWN_USD        = [string]$risk.max_intraday_drawdown_usd
$env:PHASE5_MAX_TRADES_PER_DAY      = [string]$risk.max_trades_per_day_total
$env:PHASE5_MAX_TRADES_PER_SYMBOL   = [string]$risk.max_trades_per_symbol
$env:PHASE5_COOLDOWN_MINUTES        = [string]$risk.cooldown_minutes_after_big_loss
$env:PHASE5_NO_AVG_DOWN             = $(if ($risk.no_averaging_down) { '1' } else { '0' })
$env:PHASE5_ALLOWED_STRATEGIES      = ($risk.allowed_strategies -join ',')

Write-Host "[PHASE5-RISK] Loaded $cfgPath" -ForegroundColor Cyan
Write-Host "  Daily loss cap (USD)   : $($env:PHASE5_DAILY_LOSS_CAP_USD)"
Write-Host "  Max intraday DD (USD)  : $($env:PHASE5_MAX_DRAWDOWN_USD)"
Write-Host "  Max trades / day       : $($env:PHASE5_MAX_TRADES_PER_DAY)"
Write-Host "  Max trades / symbol    : $($env:PHASE5_MAX_TRADES_PER_SYMBOL)"
Write-Host "  Cooldown (min)         : $($env:PHASE5_COOLDOWN_MINUTES)"
Write-Host "  No averaging down      : $($env:PHASE5_NO_AVG_DOWN)"
Write-Host "  Allowed strategies     : $($env:PHASE5_ALLOWED_STRATEGIES)"