[CmdletBinding()]
param(
  [string]$OutPath = ".\logs\phase6_portfolio_state.json",

  # Hard caps (configurable later)
  [double]$MaxDailyLossUsd = 500.0,
  [double]$MaxDrawdownUsd  = 1000.0,
  [double]$MaxVarUsd       = 800.0,

  # Cooldown rule
  [int]$CooldownMinutes = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Utf8NoBom([string]$Path, [string]$Text) {
  $enc = New-Object System.Text.UTF8Encoding($false)
  $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
  $full = $Path
  if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $Path }
  $dir = Split-Path -Parent $full
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  [System.IO.File]::WriteAllText($full, $Text, $enc)
}

$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc  = (Get-Date).ToUniversalTime().ToString("o")

# Inputs (fail-closed if missing; keep 0s)
$pnlPath = ".\logs\phase5_pnl_daily.csv"  # (optional future artifact)
$dailyPnl = 0.0
$dd = 0.0
$var = 0.0
$cooldown_until_utc = ""

# TODO: wire real PnL/Equity curve + VaR model
# For now: we keep these 0s; halts only trip if upstream injects non-zero.

$halts = New-Object System.Collections.Generic.List[string]
if ($dailyPnl -le (-1.0 * $MaxDailyLossUsd)) { $halts.Add("daily_loss_cap") }
if ($dd -ge $MaxDrawdownUsd) { $halts.Add("max_drawdown") }
if ($var -ge $MaxVarUsd) { $halts.Add("var_cap") }

$ok = ($halts.Count -eq 0)
$reason = if($ok){"portfolio_ok"}else{($halts -join ",")}

$out = [ordered]@{
  ts_utc = $tsUtc
  as_of_date = $today
  ok = $ok
  reason = $reason
  limits = @{
    max_daily_loss_usd = $MaxDailyLossUsd
    max_drawdown_usd = $MaxDrawdownUsd
    max_var_usd = $MaxVarUsd
    cooldown_minutes = $CooldownMinutes
  }
  metrics = @{
    daily_pnl_usd = $dailyPnl
    drawdown_usd = $dd
    var_usd = $var
    cooldown_until_utc = $cooldown_until_utc
  }
} | ConvertTo-Json -Depth 10

Write-Utf8NoBom -Path $OutPath -Text ($out + "`n")
Write-Host ("[PHASE6] wrote {0} ok={1} reason={2}" -f $OutPath,$ok,$reason) -ForegroundColor Cyan
exit 0
