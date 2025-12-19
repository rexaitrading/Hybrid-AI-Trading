[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$today = (Get-Date).ToString("yyyy-MM-dd")
$tradesCsv = Join-Path $logs "trades.csv"
$out = Join-Path $logs "nvda_gatescore_events.jsonl"

function Safe-Float([object]$x) {
  try { return [double]$x } catch { return $null }
}

if (-not (Test-Path $tradesCsv)) {
  Write-Host "[GATESCORE-EVENTS] WARN: logs\trades.csv missing; wrote nothing (fail-closed)." -ForegroundColor Yellow
  exit 0
}

$rows = @()
try { $rows = @(Import-Csv -LiteralPath $tradesCsv) } catch { $rows = @() }

if (-not $rows) {
  Write-Host "[GATESCORE-EVENTS] WARN: trades.csv empty/unreadable; wrote nothing (fail-closed)." -ForegroundColor Yellow
  exit 0
}

$vals = @()
foreach($r in $rows) {
  $s = (($r.symbol + "")).Trim().ToUpperInvariant()
  if ($s -ne "NVDA") { continue }

  $ts = ($r.ts + "")
  if (-not $ts -or $ts.Length -lt 10) { continue }
  if ($ts.Substring(0,10) -ne $today) { continue }

  $pv = Safe-Float $r.pnl
  if ($null -eq $pv) { continue }

  $vals += $pv
}

if ($vals.Count -lt 1) {
  Write-Host "[GATESCORE-EVENTS] WARN: no NVDA pnl samples for today; wrote nothing (fail-closed)." -ForegroundColor Yellow
  exit 0
}

$mean = ($vals | Measure-Object -Average).Average

# Simple bounded proxy score (placeholder until true GateScore events are wired)
$score = [Math]::Max(-1.0, [Math]::Min(1.0, [double]$mean))

$line = (@{
  as_of_date = $today
  score = [double]("{0:F6}" -f $score)
  source = "REAL"
  notes = "proxy_from_trades_csv"
} | ConvertTo-Json -Compress)

# Write UTF-8 no BOM
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($out, $line + "`n", $utf8NoBom)

Write-Host "[GATESCORE-EVENTS] OK: wrote logs\nvda_gatescore_events.jsonl" -ForegroundColor Green
Get-Content $out -TotalCount 1
exit 0
