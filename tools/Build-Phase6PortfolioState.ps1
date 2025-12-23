[CmdletBinding()]
param(
  [string]$OutPath = ".\logs\phase6_portfolio_state.json"
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
  $t = $Text -replace "`r`n","`n"
  if(-not $t.EndsWith("`n")){ $t += "`n" }
  [System.IO.File]::WriteAllText($full, $t, $enc)
}

$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

# Limits (conservative defaults; wire to your real risk config later)
$limits = [ordered]@{
  max_daily_loss_usd = 500.0
  max_drawdown_usd   = 800.0
  max_var_usd        = 600.0
  cooldown_minutes   = 30
}

# Metrics (paper-first placeholders; wire to real portfolio tracker later)
$metrics = [ordered]@{
  daily_pnl_usd        = 0.0
  drawdown_usd         = 0.0
  var_usd              = 0.0
  cooldown_until_utc   = ""
}

# Fail-closed logic for Phase6 "ok"
$ok = $true
$reason = "portfolio_ok"
if ([double]$metrics.daily_pnl_usd -le (-1.0 * [double]$limits.max_daily_loss_usd)) { $ok = $false; $reason = "daily_loss_limit_hit" }
if ([double]$metrics.drawdown_usd -ge [double]$limits.max_drawdown_usd)             { $ok = $false; $reason = "drawdown_limit_hit" }
if ([double]$metrics.var_usd -ge [double]$limits.max_var_usd)                       { $ok = $false; $reason = "var_limit_hit" }

$out = [ordered]@{
  ts_utc    = $tsUtc
  as_of_date= $today
  ok        = $ok
  reason    = $reason
  limits    = $limits
  metrics   = $metrics
} | ConvertTo-Json -Depth 8

Write-Utf8NoBom -Path $OutPath -Text $out
Write-Host "[PHASE6] wrote portfolio state -> $OutPath ok=$ok reason=$reason" -ForegroundColor Cyan
exit 0
