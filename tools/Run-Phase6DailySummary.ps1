[CmdletBinding()]
param(
  [string]$AsOfDate = "",
  [string]$OutDir = "logs\phase6"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path ".").Path
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "[PHASE6] Python missing: $py" }

$env:PYTHONNOUSERSITE="1"
$env:PYTHONPATH = (Join-Path $root "src")
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"

if (-not $AsOfDate) { $AsOfDate = (Get-Date).ToString("yyyy-MM-dd") }

Write-Host "[PHASE6] as_of_date=$AsOfDate" -ForegroundColor Cyan
& $py -m hybrid_ai_trading.phase6.daily_summary --as-of-date $AsOfDate --outdir $OutDir
exit $LASTEXITCODE