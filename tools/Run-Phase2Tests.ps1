[CmdletBinding()]
param(
  [switch]$ExitWithCode
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$old = $env:PYTHONPATH
try {
  $env:PYTHONPATH = (Resolve-Path .\src).Path
  .\.venv\Scripts\python -m pytest -q .\tests\test_phase2_costs_scaffold.py
  $ec = $LASTEXITCODE
  Write-Host "[PHASE2] pytest_exitcode=$ec" -ForegroundColor DarkGray
  if ($ExitWithCode) { exit $ec }
}
finally {
  $env:PYTHONPATH = $old
}