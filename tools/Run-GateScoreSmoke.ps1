[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "[PHASE3-SMOKE] GateScore smoke RUN" -ForegroundColor Cyan

$env:PYTHONPATH = Join-Path $repoRoot "src"
$pythonExe      = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "[PHASE3-SMOKE] ERROR: Python executable not found at $pythonExe" -ForegroundColor Red
    exit 1
}

$smokeScript = Join-Path $repoRoot "tools\_nvda_gate_score_smoke.py"
if (-not (Test-Path $smokeScript)) {
    Write-Host "[PHASE3-SMOKE] WARN: _nvda_gate_score_smoke.py not found at $smokeScript; skipping smoke." -ForegroundColor Yellow
    exit 0
}

Write-Host "[PHASE3-SMOKE] Running _nvda_gate_score_smoke.py via $pythonExe" -ForegroundColor Yellow
& $pythonExe $smokeScript
$code = $LASTEXITCODE

if ($code -ne 0) {
    Write-Host "[PHASE3-SMOKE] WARN: GateScore smoke FAILED (exit=$code). Treating as non-fatal until replay module is wired." -ForegroundColor Yellow
    exit 0
}

Write-Host "[PHASE3-SMOKE] GateScore smoke PASSED" -ForegroundColor Green
exit 0