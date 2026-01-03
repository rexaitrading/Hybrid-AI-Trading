[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Symbol,
  [Parameter(Mandatory=$true)][string]$AsOfDate  # YYYY-MM-DD
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$py = Join-Path $repo ".venv\Scripts\python.exe"
if(-not (Test-Path $py)){ throw "Missing venv python: $py" }

$ibHist = Join-Path $repo "src\hybrid_ai_trading\ib\ib_history_fetch.py"
if(-not (Test-Path $ibHist)){
  Write-Host "[IBKR] FAIL-CLOSED: missing history fetcher: $ibHist" -ForegroundColor Yellow
  Write-Host "[IBKR] Use tools\Put-BarsCsv.ps1 to populate logs\bars\SYMBOL_YYYY-MM-DD_1m.csv for now." -ForegroundColor Yellow
  exit 2
}

& $py -m hybrid_ai_trading.ib.ib_history_fetch --symbol $Symbol --as-of-date $AsOfDate
exit $LASTEXITCODE