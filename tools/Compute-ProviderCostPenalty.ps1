[CmdletBinding()]
param(
  [string]$PolicyPath = ".\config\providers_policy.json",
  [int]$TradesPerDay = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

if(-not (Test-Path -LiteralPath $PolicyPath)){ throw "Missing: $PolicyPath" }

$j = Get-Content -LiteralPath $PolicyPath -Raw -Encoding utf8 | ConvertFrom-Json
$defaults = $j.defaults
if($null -eq $defaults){ throw "Invalid policy: missing defaults" }

$maxBudget = [double]($defaults.max_monthly_budget_usd)
$td = [int]($defaults.trading_days_per_month)
if($td -lt 1){ $td = 21 }

$costPerDay = $maxBudget / [double]$td
$costPerTrade = $costPerDay / [double][Math]::Max(1,$TradesPerDay)

[ordered]@{
  version = "provider_cost_penalty.1"
  policy_path = $PolicyPath
  max_monthly_budget_usd = $maxBudget
  trading_days_per_month = $td
  trades_per_day = $TradesPerDay
  cost_per_day_usd = [Math]::Round($costPerDay, 4)
  cost_per_trade_usd = [Math]::Round($costPerTrade, 6)
} | ConvertTo-Json -Depth 5

exit 0
