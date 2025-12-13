[CmdletBinding()]
param(
  [string]$PyExe = ".\.venv\Scripts\python.exe",
  [string]$PyArgs = "-m pytest -q",
  [string]$TestFilter = "blockg or runcontext or gatescore_daily or phase4_validation",
  [int]$TimeoutSec = 0
)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

if (-not (Test-Path $PyExe)) {
  Write-Host "[PHASE4] ERROR: python not found at $PyExe" -ForegroundColor Red
  exit 2
}

$env:PYTHONPATH = Join-Path $repoRoot 'src'

Write-Host "[PHASE4] RepoRoot=$repoRoot" -ForegroundColor Cyan
Write-Host "[PHASE4] PyExe=$PyExe" -ForegroundColor Cyan
Write-Host "[PHASE4] PYTHONPATH=$env:PYTHONPATH" -ForegroundColor Cyan
Write-Host "[PHASE4] Filter=$TestFilter" -ForegroundColor Cyan

# NOTE: keep broad filter until you add dedicated markers; this is the stable minimal â€œsmokeâ€
$cmd = "$PyArgs tests -k `"$TestFilter`""
Write-Host "[PHASE4] CMD: $PyExe $cmd" -ForegroundColor DarkGray

# Execute
& $PyExe @("-m","pytest","-q","tests","-k",$TestFilter)
$ec = $LASTEXITCODE

if ($ec -ne 0) {
  Write-Host "[PHASE4] FAIL exit=$ec" -ForegroundColor Red
  exit $ec
}

Write-Host "[PHASE4] PASS" -ForegroundColor Green
exit 0
