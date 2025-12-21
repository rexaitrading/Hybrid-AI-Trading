[CmdletBinding()]
param(
  [string]$AsOfDate = "",
  [string]$OutDir = "logs\phase7",
  [string]$Symbols = "NVDA,SPY,QQQ",
  [double]$MaxWeight = 0.60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path ".").Path
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "[PHASE7] Python missing: $py" }

$env:PYTHONNOUSERSITE="1"
$env:PYTHONPATH = (Join-Path $root "src")
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"

# deterministic Block-G contract path
$k = ("HAT_" + "BLOCKG_" + "STATUS_" + "PATH")
[System.Environment]::SetEnvironmentVariable($k, (Join-Path $root "logs\blockg_status_stub.json"))

if (-not $AsOfDate) { $AsOfDate = (Get-Date).ToString("yyyy-MM-dd") }

Write-Host "[PHASE7] as_of_date=$AsOfDate symbols=$Symbols max_weight=$MaxWeight" -ForegroundColor Cyan
& $py -m hybrid_ai_trading.phase7.optimizer --as-of-date $AsOfDate --outdir $OutDir --symbols $Symbols --max-weight $MaxWeight
exit $LASTEXITCODE