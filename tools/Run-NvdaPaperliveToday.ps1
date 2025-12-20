[CmdletBinding()]
param(
  [int]$MinEvents = 120,
  [string]$OutPath = ".\logs\nvda_phase5_paperlive_results_today.jsonl",
  [double]$Edge = 0.03,
  [double]$Micro = 0.60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "venv python not found at $py" }

Write-Host "[NVDA-PAPERLIVE] Building today paperlive inputs" -ForegroundColor Cyan

& $py -m hybrid_ai_trading.runners.nvda_paperlive_today `
  --out $OutPath `
  --n $MinEvents `
  --regime NVDA_BPLUS_LIVE `
  --edge ([string]$Edge) `
  --micro ([string]$Micro) `
  --pnl-samples 1 `
  --price 0.0 `
  --local-start 09:30:00

$ec = $LASTEXITCODE
if ($ec -ne 0) {
  Write-Host "[NVDA-PAPERLIVE] ERROR: producer exit=$ec" -ForegroundColor Red
  exit $ec
}

if (-not (Test-Path $OutPath)) {
  Write-Host "[NVDA-PAPERLIVE] ERROR: output not created: $OutPath" -ForegroundColor Red
  exit 2
}

$cnt = @(Get-Content $OutPath).Count
Write-Host "[NVDA-PAPERLIVE] Wrote rows=$cnt -> $OutPath" -ForegroundColor Green

if ($cnt -lt $MinEvents) {
  Write-Host "[NVDA-PAPERLIVE] ERROR: too few rows ($cnt < $MinEvents)" -ForegroundColor Red
  exit 4
}

exit 0
