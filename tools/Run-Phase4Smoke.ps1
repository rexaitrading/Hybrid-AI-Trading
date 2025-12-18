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

function Resolve-RepoRoot {
  # start from the directory containing this script
  $here = Split-Path -Parent $MyInvocation.MyCommand.Path
  $d = (Resolve-Path $here).Path

  while($true){
    if(Test-Path (Join-Path $d ".git")){ return $d }
    $parent = Split-Path -Parent $d
    if([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $d){ break }
    $d = $parent
  }

  throw "PhaseSweep: Could not find .git by walking up from script dir: $here"
}

$repoRoot = Resolve-RepoRoot
Set-Location $repoRoot


# --- PHASE4_STAMP_SINGLE_TRUTH ---
# Write today's phase4_validation_passed.json based on smoke result.
try {
  $phase4Ok = "0"
  if ($LASTEXITCODE -eq 0) { $phase4Ok = "1" }

  if (Test-Path ".\tools\Write-Phase4PassedStamp.ps1") {
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\Write-Phase4PassedStamp.ps1" -Phase4Ok $phase4Ok | Out-Host
  } else {
    Write-Host "[PHASE4] WARN: Write-Phase4PassedStamp.ps1 not found; stamp not written." -ForegroundColor Yellow
  }
} catch {
  Write-Host "[PHASE4] WARN: stamp write failed (non-fatal): $($_.Exception.Message)" -ForegroundColor Yellow
}
# --- END PHASE4_STAMP_SINGLE_TRUTH ---