[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$py = Join-Path $repoRoot ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "[GATESCORE-SAMPLES] missing python: $py" }

Write-Host "[GATESCORE-SAMPLES] Emit NVDA GateScore samples (replay-driven)..." -ForegroundColor Cyan
& $py .\tools\emit_nvda_gatescore_samples.py
Write-Host "[GATESCORE-SAMPLES] ExitCode=$LASTEXITCODE" -ForegroundColor DarkCyan

$out = Join-Path $repoRoot "logs\nvda_gatescore_samples.csv"
if (Test-Path $out) {
  Get-Content $out -TotalCount 3
} else {
  Write-Host "[GATESCORE-SAMPLES] WARN: no output file produced (fail-closed)" -ForegroundColor Yellow
}
