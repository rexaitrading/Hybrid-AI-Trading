[CmdletBinding()]
param(
  [string]$PyExe = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

if (-not (Test-Path $PyExe)) {
  Write-Host "[VALIDATION] ERROR: python not found at $PyExe" -ForegroundColor Red
  exit 2
}

$env:PYTHONPATH = Join-Path $repoRoot 'src'

function Run-Py([string[]]$Args) {
  Write-Host "`n[PY] $PyExe $($Args -join ' ')" -ForegroundColor DarkGray
  & $PyExe @Args
  $ec = $LASTEXITCODE
  if ($ec -ne 0) {
    Write-Host "[PY] FAIL exit=$ec" -ForegroundColor Red
    exit $ec
  }
  Write-Host "[PY] OK" -ForegroundColor Green
}

# 1) Import-level sanity (fast)
Run-Py @("-c", "import hybrid_ai_trading.runtime.context_loader as c; print('context_loader OK')")

# 2) Phase-4 smoke (python side is called inside ps script, but keep this import-level check)
Run-Py @("-c", "import hybrid_ai_trading.execution.blockg_contract as b; print('blockg_contract OK')")

# 3) Runner smoke that we know is green
Run-Py @("-m","pytest","-q","tests/test_runner_cover_all.py","-q")

Write-Host "`n[VALIDATION] STACK PASS" -ForegroundColor Green
exit 0
