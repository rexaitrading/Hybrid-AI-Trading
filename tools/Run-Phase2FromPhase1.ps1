[CmdletBinding()]
param(
  [string]$Session = "logs\replay\replay_session.json",
  [string]$OutDir = "logs\phase2",
  [int]$MaxRows = 0
)


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
# $toolsDir = Split-Path -Parent $PSCommandPath   # disabled (use env HAT_REPO_ROOT)
# $repoRoot = Split-Path -Parent $toolsDir        # disabled (use env HAT_REPO_ROOT)
# Set-Location $repoRoot                          # disabled (use env HAT_REPO_ROOT)
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Python missing: $py" }
$env:PYTHONPATH = Join-Path $repoRoot "src"

if (-not (Test-Path -LiteralPath $Session)) { throw "Phase2: session missing: $Session" }
if (-not (Test-Path -LiteralPath $OutDir)) { New-Item -ItemType Directory -Force -Path $OutDir | Out-Null }

& $py -m hybrid_ai_trading.phase2.run_from_phase1 --session $Session --outdir $OutDir --max_rows $MaxRows
exit $LASTEXITCODE