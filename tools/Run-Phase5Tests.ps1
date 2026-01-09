[CmdletBinding()]
param()


# --- repo root bootstrap (env-first) ---
$repoRoot = ($env:HAT_REPO_ROOT + "").Trim()
if(-not $repoRoot){
  $repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
}
if(-not $repoRoot){ throw "[REPOROOT] FAIL-CLOSED: repoRoot empty (env+Go-RepoRoot)" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
# Set-Location $repoRoot                          # disabled (use env HAT_REPO_ROOT)
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Python exe not found: $py" }

$env:PYTHONPATH = Join-Path $repoRoot "src"

& $py -m pytest -q `
  tests/test_phase5_ev_bands_basic.py `
  tests/test_phase5_riskmanager_combined_gates.py `
  tests/test_phase5_riskmanager_daily_loss_integration.py `
  tests/test_execution_engine_phase5_guard.py `
  tests/test_ib_phase5_guard.py
exit $LASTEXITCODE