[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [ValidateSet("SPY","QQQ","NVDA")]
  [string]$Symbol,

  # Force DEV_REPLAY for paper-derived samples (cannot arm live)
  [ValidateSet("DEV_REPLAY")]
  [string]$Mode = "DEV_REPLAY"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
$today = (Get-Date).ToString("yyyy-MM-dd")

$inJsonl = Join-Path $logs ("{0}_phase5_paperlive_results.jsonl" -f $Symbol.ToLowerInvariant())
if (-not (Test-Path $inJsonl)) {
  throw "Missing input: $inJsonl"
}

$outCsv = Join-Path $logs ("{0}_gatescore_samples.csv" -f $Symbol.ToLowerInvariant())

# Read JSONL and filter to today
$rows = @()
Get-Content $inJsonl -Encoding utf8 | ForEach-Object {
  $ln = $_.Trim()
  if (-not $ln) { return }
  try { $obj = $ln | ConvertFrom-Json -ErrorAction Stop } catch { return }
  $ts = "$($obj.ts_trade)"
  if ($ts.Length -ge 10 -and $ts.Substring(0,10) -eq $today) {
    $rows += $obj
  }
}

# Fail-closed: if no rows, write header only
"as_of_date,samples,score,count_signals,pnl_samples" | Out-File -FilePath $outCsv -Encoding ascii
if (-not $rows -or $rows.Count -lt 1) {
  Write-Host "[GS-SAMPLES] WARN: no $Symbol rows for today; wrote header-only $outCsv" -ForegroundColor Yellow
  exit 0
}

# Compute a conservative score proxy from EV (mean of 'ev' fields if present; else 0.0)
$evs = @()
foreach ($r in $rows) {
  if ($null -ne $r.ev) {
    try { $evs += [double]("$($r.ev)") } catch { }
  }
}

$score = 0.0
if ($evs.Count -gt 0) {
  $score = ($evs | Measure-Object -Average).Average
}

$samples = [int]$rows.Count
$count_signals = $samples
$pnl_samples = $samples

# Append one sample row for today
"{0},{1},{2:F6},{3},{4}" -f $today,$samples,$score,$count_signals,$pnl_samples |
  Out-File -FilePath $outCsv -Encoding ascii -Append

Write-Host "[GS-SAMPLES] Wrote $outCsv symbol=$Symbol samples=$samples score=$('{0:F6}' -f $score) mode=$Mode" -ForegroundColor Green
exit 0