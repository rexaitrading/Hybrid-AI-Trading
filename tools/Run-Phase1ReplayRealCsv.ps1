[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",
[Parameter(Mandatory=$true)]
  [string]$InputCsv,

  [Parameter(Mandatory=$false)]
  [string]$Config = "config/paper_runner.yaml",

  [Parameter(Mandatory=$false)]
  [string]$OutLog = "",

  [Parameter(Mandatory=$false)]
  [string]$OutDir = "",

  [Parameter(Mandatory=$false)]
  [int]$Batch = 100)


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
if (-not (Test-Path $InputCsv)) { throw "Phase1 input CSV not found: $InputCsv" }

$logsDir = Join-Path $repoRoot "logs\phase1"
if ($OutDir) {
  $logsDir = Join-Path $repoRoot $OutDir
}New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

if (-not $OutLog) {
  $stamp = Get-Date -Format yyyyMMdd_HHmmss
  $OutLog = (Join-Path $logsDir ("phase1_replay_real_{0}.jsonl" -f $stamp))
}

# Use repo venv python if present, else fallback to 'python'
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

Write-Host ("[PHASE1] RepoRoot={0}" -f $repoRoot) -ForegroundColor Cyan
Write-Host ("[PHASE1] InputCsv={0}" -f (Resolve-Path $InputCsv).Path) -ForegroundColor Cyan
Write-Host ("[PHASE1] OutLog={0}" -f $OutLog) -ForegroundColor Cyan

# Canonical Phase1 replay entrypoint (exists in your repo)
$entry = Join-Path $repoRoot "runners\backtest_replay.py"
if (-not (Test-Path $entry)) { throw "Missing runners/backtest_replay.py at $entry" }

& $py $entry --config $Config --input $InputCsv --log $OutLog --batch $Batch
if ($LASTEXITCODE -ne 0) { throw "Phase1 replay failed (exit=$LASTEXITCODE)" }

Write-Host "[PHASE1] OK" -ForegroundColor Green
exit 0