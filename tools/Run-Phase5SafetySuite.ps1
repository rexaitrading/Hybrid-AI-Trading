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

$repoRoot = (Resolve-Path ".").Path
$py = Join-Path (& (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")) ".venv\Scripts\python.exe"
if(-not (Test-Path $py)){ throw "python not found: $py" }
# Pytest temp must NOT be under OneDrive (WinError 5). Use local TEMP.
$baseTemp = Join-Path $env:TEMP "HybridAITrading\pytest_tmp"
New-Item -ItemType Directory -Force -Path $baseTemp | Out-Null
$env:HAT_PYTEST_BASETEMP = $baseTemp

& $py -m pytest -q --basetemp $baseTemp `
  .\tests\test_execution_engine_phase5_guard.py `
  .\tests\test_ib_phase5_guard.py `
  .\tests\test_blockg_broker_base_guard.py `
  .\tests\test_blockg_risk_flatten_guard.py `
  .\tests\test_runcontext_precedence.py

exit $LASTEXITCODE
