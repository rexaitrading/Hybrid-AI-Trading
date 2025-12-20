[CmdletBinding()]
param(
  [string]$Session = "logs\replay\replay_session.json",
  [string]$OutDir = "logs\phase2",
  [int]$MaxRows = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Python missing: $py" }
$env:PYTHONPATH = Join-Path $repoRoot "src"

if (-not (Test-Path -LiteralPath $Session)) { throw "Phase2: session missing: $Session" }
if (-not (Test-Path -LiteralPath $OutDir)) { New-Item -ItemType Directory -Force -Path $OutDir | Out-Null }

& $py -m hybrid_ai_trading.phase2.run_from_phase1 --session $Session --outdir $OutDir --max_rows $MaxRows
exit $LASTEXITCODE