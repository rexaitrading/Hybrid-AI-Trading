[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol="NVDA",

  [double]$MaxNotionalUsd = 25000,   # placeholder cap
  [double]$MaxVarUsd = 1500,         # placeholder VaR cap
  [double]$MaxConcentrationPct = 0.60 # placeholder: NVDA max 60% of portfolio
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Fail([string]$msg){
  Write-Host "[PORTFOLIO] NOT READY: $msg" -ForegroundColor Red
  exit 2
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$logsDir  = Join-Path $repoRoot "logs"
$statusPath = Join-Path $logsDir "portfolio_gate_status.json"

# NOTE: This is a fail-closed skeleton. It becomes real once portfolio_state/metrics are wired.
$metricsPath = Join-Path $logsDir "phase6_portfolio_metrics.json"
$statePath   = Join-Path $logsDir "phase6_portfolio_state.json"

$reasons = New-Object System.Collections.Generic.List[string]

if(-not (Test-Path $metricsPath)){ $reasons.Add("missing_phase6_portfolio_metrics.json") | Out-Null }
if(-not (Test-Path $statePath)){   $reasons.Add("missing_phase6_portfolio_state.json")   | Out-Null }

# If missing any core file => fail-closed (until Phase7 is truly wired)
if($reasons.Count -gt 0){
  $payload = [ordered]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    as_of_date = (Get-Date).ToString("yyyy-MM-dd")
    symbol = $Symbol
    ok = $false
    reasons_not_ready = @($reasons)
  } | ConvertTo-Json -Depth 6
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($statusPath, $payload, $utf8NoBom)
  Fail ("portfolio_gate_failclosed (see " + $statusPath + ")")
}

# TODO: parse metrics/state; enforce VaR, concentration, correlation, scaling clamp.
# For now, if files exist, mark ok=true (still conservative until real checks are implemented).
$payload = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date = (Get-Date).ToString("yyyy-MM-dd")
  symbol = $Symbol
  ok = $true
  notes = @("skeleton_ok_files_present_only","wire_real_checks_next")
} | ConvertTo-Json -Depth 6

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($statusPath, $payload, $utf8NoBom)

Write-Host "[PORTFOLIO] READY (skeleton): Symbol=$Symbol" -ForegroundColor Green
exit 0