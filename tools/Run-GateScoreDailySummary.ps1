[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol="ALL"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc  = (Get-Date).ToUniversalTime().ToString("o")

$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$outCsv = Join-Path $logDir "gatescore_daily_summary.csv"

# Canonical schema expected by Build-BlockGStatusStub.ps1
$header = "as_of_date,symbol,count_signals,pnl_samples,mean_edge_ratio,mean_micro_score"

$syms = @("NVDA","SPY","QQQ")
if ($Symbol -ne "ALL") { $syms = @($Symbol.ToUpperInvariant()) }

# Load existing rows safely (handle missing file)
$rows = @()
if (Test-Path $outCsv) {
  try { $rows = @(Import-Csv $outCsv) } catch { $rows = @() }
} else {
  Set-Content -LiteralPath $outCsv -Encoding utf8 -Value $header
}

# Keep rows that are NOT (today + target symbol)
$kept = New-Object System.Collections.Generic.List[object]
foreach($r in $rows){
  $d = ""
  if ($r.PSObject.Properties.Name -contains "as_of_date") { $d = [string]$r.as_of_date }
  if ($d.Length -ge 10) { $d = $d.Substring(0,10) }

  $sym = ""
  if ($r.PSObject.Properties.Name -contains "symbol") { $sym = ([string]$r.symbol).ToUpperInvariant() }

  if ($d -eq $today -and ($syms -contains $sym)) { continue }

  # Normalize into canonical shape (ignore extra columns)
  $kept.Add([pscustomobject]@{
    as_of_date = $d
    symbol = $sym
    count_signals = [int]($r.count_signals -as [int])
    pnl_samples = [int]($r.pnl_samples -as [int])
    mean_edge_ratio = [double]($r.mean_edge_ratio -as [double])
    mean_micro_score = [double]($r.mean_micro_score -as [double])
  }) | Out-Null
}

# TODO: replace these stub metrics with real daily GateScore build outputs.
# For now, emit deterministic zeros for today (fail-closed).
foreach($sym in $syms){
  $kept.Add([pscustomobject]@{
    as_of_date = $today
    symbol = $sym
    count_signals = 0
    pnl_samples = 0
    mean_edge_ratio = 0.0
    mean_micro_score = 0.0
  }) | Out-Null
}

# Write canonical CSV (UTF-8 no-BOM)
$lines = New-Object System.Collections.Generic.List[string]
$lines.Add($header) | Out-Null
foreach($r in $kept){
  $lines.Add(("{0},{1},{2},{3},{4},{5}" -f $r.as_of_date,$r.symbol,$r.count_signals,$r.pnl_samples,$r.mean_edge_ratio,$r.mean_micro_score)) | Out-Null
}
[System.IO.File]::WriteAllLines($outCsv, $lines, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "[GS] wrote $outCsv today=$today symbols=$($syms -join ',')" -ForegroundColor Green
exit 0
