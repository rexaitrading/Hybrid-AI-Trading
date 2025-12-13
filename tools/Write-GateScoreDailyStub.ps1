[CmdletBinding()]
param(
  [string]$Symbol = "NVDA",
  [int]$CountSignals = 5,
  [int]$PnlSamples = 4,
  [double]$MeanEdgeRatio = 0.01,
  [double]$MeanMicroScore = 0.0
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs -Force | Out-Null }

$out = Join-Path $logs "gatescore_daily_summary.csv"
$today = (Get-Date).ToString("yyyy-MM-dd")

# Header expected by Build-BlockGStatusStub.ps1
$header = "as_of_date,symbol,count_signals,pnl_samples,mean_edge_ratio,mean_micro_score"

if (-not (Test-Path $out) -or (Get-Item $out).Length -eq 0) {
  $header | Out-File -FilePath $out -Encoding ascii
}

# Append today row
("$today,$Symbol,$CountSignals,$PnlSamples,$MeanEdgeRatio,$MeanMicroScore") | Out-File -FilePath $out -Append -Encoding ascii

Write-Host "[GATESCORE] Wrote/updated $out with today row for $Symbol" -ForegroundColor Green
return