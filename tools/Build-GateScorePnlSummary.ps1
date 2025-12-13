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

$logs = Join-Path $repoRoot "logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$today = (Get-Date).ToString("yyyy-MM-dd")
$sym   = (($Symbol + "")).Trim().ToUpper()
if (-not $sym) { throw "Symbol empty" }

$out = Join-Path $logs "gatescore_pnl_summary.csv"

# ------------------------------------------
# FAIL-CLOSED: if we can't find real inputs,
# we write HEADER ONLY (no today row).
# The smoke will then treat as missing/invalid.
# ------------------------------------------

# Candidate sources (add more as you confirm your real pipelines):
$candidates = @(
  (Join-Path $logs "nvda_phase5_paperlive_results.jsonl"),
  (Join-Path $logs "nvda_phase5_live_results.jsonl"),
  (Join-Path $logs "phase5_paperlive_results.jsonl"),
  (Join-Path $logs "phase5_live_results.jsonl"),
  (Join-Path $logs "paper_trades.jsonl"),
  (Join-Path $logs "trades.jsonl")
)

$input = $null
foreach($c in $candidates){
  if(Test-Path $c){ $input = $c; break }
}

# Header schema (stable)
# Keep minimal + extensible.
$header = "as_of_date,symbol,realized_pnl"

if (-not $input) {
  Write-Utf8NoBom -Path $out -Content ($header + "`r`n")
  Write-Host "[GATESCORE-PNL] WARN: no real trade source found; wrote header-only logs\gatescore_pnl_summary.csv (fail-closed)." -ForegroundColor Yellow
  exit 0
}

# Parse JSONL best-effort.
# Expected line shapes vary; we handle common keys:
#   symbol / sym
#   date / as_of_date / day / ts
#   realized_pnl / pnl / realized / realized_pnl_usd
$sum = 0.0
$found = 0

Get-Content -LiteralPath $input -ErrorAction Stop | ForEach-Object {
  $line = $_.Trim()
  if (-not $line) { return }

  try { $obj = $line | ConvertFrom-Json } catch { return }

  $s = (($obj.symbol + "")).Trim().ToUpper()
  if (-not $s) { $s = (($obj.sym + "")).Trim().ToUpper() }
  if ($s -ne $sym) { return }

  $d = ($obj.as_of_date + "")
  if (-not $d) { $d = ($obj.date + "") }
  if (-not $d) { $d = ($obj.day + "") }
  if (-not $d) {
    # try ts -> yyyy-mm-dd
    $ts = ($obj.ts + "")
    if ($ts -and $ts.Length -ge 10) { $d = $ts.Substring(0,10) }
  }
  if (-not $d) { return }
  $d = $d.Substring(0, [Math]::Min(10, $d.Length))
  if ($d -ne $today) { return }

  $p = $null
  foreach($k in @("realized_pnl","pnl","realized","realized_pnl_usd")){
    if ($null -ne $obj.$k) { $p = $obj.$k; break }
  }
  if ($null -eq $p) { return }

  $pv = 0.0
  try { $pv = [double]$p } catch { return }

  $sum += $pv
  $found += 1
}

# Write output
if ($found -le 0) {
  Write-Utf8NoBom -Path $out -Content ($header + "`r`n")
  Write-Host "[GATESCORE-PNL] WARN: input found but no rows matched ($sym, $today); wrote header-only (fail-closed)." -ForegroundColor Yellow
  exit 0
}

$body = @()
$body += $header
$body += ("{0},{1},{2}" -f $today, $sym, ("{0:F2}" -f $sum))
Write-Utf8NoBom -Path $out -Content (($body -join "`r`n") + "`r`n")

Write-Host "[GATESCORE-PNL] OK: wrote logs\gatescore_pnl_summary.csv (rows=$found sum=$sum)" -ForegroundColor Green
Get-Content -LiteralPath $out -TotalCount 2
exit 0