[CmdletBinding()]
param(
  [ValidateSet("REAL")]
  [string]$Mode = "REAL"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
$today = (Get-Date).ToString("yyyy-MM-dd")

$inJsonl  = Join-Path $logs "qqq_phase5_paperlive_results.jsonl"
$outJsonl = Join-Path $logs "qqq_gatescore_events.jsonl"

if (-not (Test-Path $inJsonl)) { throw "Missing input: $inJsonl" }

"" | Out-File -FilePath $outJsonl -Encoding utf8

$rows = 0
Get-Content $inJsonl -Encoding utf8 | ForEach-Object {
  $ln = $_.Trim()
  if (-not $ln) { return }
  try { $obj = $ln | ConvertFrom-Json -ErrorAction Stop } catch { return }
  $ts = "$($obj.ts_trade)"
  if ($ts.Length -lt 10) { return }
  if ($ts.Substring(0,10) -ne $today) { return }

  $score = 0.0
  if ($null -ne $obj.ev) {
    try { $score = [double]("$($obj.ev)") } catch { $score = 0.0 }
  }

  $evt = [ordered]@{
    as_of_date     = $today
    symbol         = "QQQ"
    source         = "REAL"
    score          = $score
    count_signals  = 1
    pnl_samples    = 1
  } | ConvertTo-Json -Compress

  Add-Content -Path $outJsonl -Value $evt -Encoding utf8
  $rows++
}

if ($rows -eq 0) {
  Write-Host "[GS-EVENTS] WARN: no QQQ rows for today; wrote empty $outJsonl" -ForegroundColor Yellow
  exit 0
}

Write-Host "[GS-EVENTS] Wrote $outJsonl rows=$rows mode=$Mode" -ForegroundColor Green
exit 0