[CmdletBinding()]
param(
  [string[]]$PytestArgs = @()
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = (Get-Location).Path
$src  = Join-Path $root "src"
$py   = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

# Hard lock: ignore user-site and force this repo's src
$env:PYTHONNOUSERSITE = "1"
$env:PYTHONPATH = $src

Write-Host "[PYTEST] ROOT=$root" -ForegroundColor Cyan
Write-Host "[PYTEST] PYTHONPATH=$env:PYTHONPATH" -ForegroundColor Cyan
Write-Host "[PYTEST] PYTHONNOUSERSITE=$env:PYTHONNOUSERSITE" -ForegroundColor Cyan

& $py -c "import os,sys,hybrid_ai_trading; print('[PYTEST] hybrid_ai_trading.__file__=', hybrid_ai_trading.__file__); print('[PYTEST] PATH_HAS_ONEDRIVE=', any('OneDrive' in p for p in sys.path))"

if ($PytestArgs.Count -gt 0) {
  & $py -m pytest --rootdir $root .\tests @PytestArgs
} else {
  & $py -m pytest -q .\tests -k "execution_engine_full or blockg_enforce or trade_engine_micro_duo" --maxfail=1
}

exit $LASTEXITCODE