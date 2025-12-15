[CmdletBinding()]
param(
  [Parameter()][string]$Symbol = "NVDA"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

function Write-Utf8NoBom([string]$Path, [string]$Content) {
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Safe-Float([object]$x) {
  try { return [double]$x } catch { return $null }
}

$logs = Join-Path $repoRoot "logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$today = (Get-Date).ToString("yyyy-MM-dd")
$sym   = (($Symbol + "")).Trim().ToUpper()
if (-not $sym) { throw "Symbol empty" }

$out = Join-Path $logs "gatescore_pnl_summary.csv"
$tradesCsv = Join-Path $logs "trades.csv"

Write-Host ("[GATESCORE-PNL] repoRoot={0}" -f $repoRoot) -ForegroundColor DarkCyan
Write-Host ("[GATESCORE-PNL] logs={0}" -f $logs) -ForegroundColor DarkCyan
Write-Host ("[GATESCORE-PNL] tradesCsv={0} exists={1}" -f $tradesCsv, (Test-Path $tradesCsv)) -ForegroundColor DarkCyan
# Match smoke expectation: always output these columns.
# (mean_edge_ratio/mean_micro_score are placeholders until you wire real metrics)
$header = "as_of_date,symbol,count_signals,pnl_samples,mean_edge_ratio,mean_micro_score,mean_pnl"

if (-not (Test-Path $tradesCsv)) {
  Write-Utf8NoBom -Path $out -Content ($header + "`r`n")
  Write-Host "[GATESCORE-PNL] WARN: logs\trades.csv missing; wrote header-only (fail-closed)." -ForegroundColor Yellow
  exit 0
}

$rows = @()
try { $rows = @(Import-Csv -LiteralPath $tradesCsv) } catch { $rows = @() }

if (-not $rows) {
  Write-Utf8NoBom -Path $out -Content ($header + "`r`n")
  Write-Host "[GATESCORE-PNL] WARN: trades.csv empty/unreadable; wrote header-only (fail-closed)." -ForegroundColor Yellow
  exit 0
}

# trades.csv header you showed:
# ts,strategy,broker,symbol,side,qty,px,order_type,order_id,status,pnl,meta,risk
# We treat "pnl" as realized pnl sample, and "ts" as date source.

$vals = @()
foreach($r in $rows) {
  $s = (($r.symbol + "")).Trim().ToUpper()
  if ($s -ne $sym) { continue }

  $ts = ($r.ts + "")
  if (-not $ts -or $ts.Length -lt 10) { continue }
  $d = $ts.Substring(0,10)
  if ($d -ne $today) { continue }

  $pv = Safe-Float $r.pnl
  if ($null -eq $pv) { continue }

  $vals += $pv
}

if ($vals.Count -lt 1) {
  Write-Utf8NoBom -Path $out -Content ($header + "`r`n")
  Write-Host "[GATESCORE-PNL] WARN: no REAL $sym pnl samples for today ($today); wrote header-only (fail-closed)." -ForegroundColor Yellow
  exit 0
}

$meanPnl = ($vals | Measure-Object -Average).Average
$countSignals = [int]$vals.Count
$pnlSamples   = [int]$vals.Count

# placeholders until you wire real edge/micro
$meanEdge  = 0.0
$meanMicro = 0.0

$line = ("{0},{1},{2},{3},{4},{5},{6}" -f `
  $today, $sym, $countSignals, $pnlSamples, `
  ("{0:F6}" -f $meanEdge), ("{0:F6}" -f $meanMicro), ("{0:F6}" -f $meanPnl))

Write-Utf8NoBom -Path $out -Content ($header + "`r`n" + $line + "`r`n")

Write-Host "[GATESCORE-PNL] OK: wrote logs\gatescore_pnl_summary.csv (pnl_samples=$pnlSamples mean_pnl=$meanPnl)" -ForegroundColor Green
Get-Content -LiteralPath $out -TotalCount 2
exit 0
