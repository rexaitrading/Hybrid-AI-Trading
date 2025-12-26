[CmdletBinding()]
param(
  [string]$Symbol = "NVDA",
  [string]$StartDate = "",
  [string]$EndDate = "",
  [string]$OutDir = "logs\replay"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

if (-not $StartDate) { $StartDate = (Get-Date).AddDays(-5).ToString("yyyy-MM-dd") }
if (-not $EndDate)   { $EndDate   = (Get-Date).ToString("yyyy-MM-dd") }

$py = ".\.venv\Scripts\python.exe"
$env:PYTHONPATH = Join-Path $repoRoot "src"

& $py -m hybrid_ai_trading.replay.replay_multi_day --symbol $Symbol --start-date $StartDate --end-date $EndDate --outdir $OutDir
exit $LASTEXITCODE