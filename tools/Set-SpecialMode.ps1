[CmdletBinding()]
param(
  [switch]$Arm,
  [switch]$Disarm,

  [string]$Name = "special",
  [string]$Reason = "operator_armed",

  [double]$MaxLeverage = 2.0,
  [double]$MaxPortfolioExposure = 0.40,
  [double]$PerTradeNotionalCap = 2000.0,

  [double]$SizeMultiplier = 1.5,
  [int]$MaxTradesPerDay = 6,

  [int]$ExpiresHours = 6
)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logsDir = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$out = Join-Path $logsDir "risk_envelope.json"
$todayUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
$expUtc = (Get-Date).ToUniversalTime().AddHours([double]$ExpiresHours).ToString("o")

if ($Disarm) {
  $obj = [ordered]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    as_of_date = $todayUtc
    armed = $false
    name = $Name
    reason = "operator_disarm"
    expires_utc = $expUtc
  }
} else {
  if (-not $Arm) { $Arm = $true } # default behavior: arm
  $obj = [ordered]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    as_of_date = $todayUtc
    armed = $true
    name = $Name
    reason = $Reason
    expires_utc = $expUtc

    max_leverage = [double]$MaxLeverage
    max_portfolio_exposure = [double]$MaxPortfolioExposure
    per_trade_notional_cap = [double]$PerTradeNotionalCap

    size_multiplier = [double]$SizeMultiplier
    max_trades_per_day = [int]$MaxTradesPerDay
  }
}

$json = ($obj | ConvertTo-Json -Depth 5)

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($out, $json, $utf8NoBom)

Write-Host "[SPECIAL] wrote $out" -ForegroundColor Green
Write-Host "[SPECIAL] IMPORTANT: Special-Mode is ACTIVE only if you also set: HAT_SPECIAL_MODE=1" -ForegroundColor Yellow
