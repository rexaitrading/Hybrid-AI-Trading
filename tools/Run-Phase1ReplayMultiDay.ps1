[CmdletBinding()]
param(
  [string]$Symbol = "NVDA",
  [string]$StartDate = "",
  [string]$EndDate = "",
  [string]$OutDir = "logs\replay"
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

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
# Set-Location $repoRoot                          # disabled (use env HAT_REPO_ROOT)
if (-not $StartDate) { $StartDate = (Get-Date).AddDays(-5).ToString("yyyy-MM-dd") }
if (-not $EndDate)   { $EndDate   = (Get-Date).ToString("yyyy-MM-dd") }

$py = ".\.venv\Scripts\python.exe"
$env:PYTHONPATH = Join-Path $repoRoot "src"

& $py -m hybrid_ai_trading.replay.replay_multi_day --symbol $Symbol --start-date $StartDate --end-date $EndDate --outdir $OutDir
exit $LASTEXITCODE