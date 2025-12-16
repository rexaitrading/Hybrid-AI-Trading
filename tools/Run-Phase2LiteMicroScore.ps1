[CmdletBinding()]
param(
  [ValidateSet("SPY","QQQ")]
  [string]$Symbol
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$py = Join-Path $repoRoot ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Missing python: $py" }

$logs = Join-Path $repoRoot "logs"
$in  = Join-Path $logs ("{0}_phase5_paperlive_results.jsonl" -f $Symbol.ToLowerInvariant())
$out = Join-Path $logs ("{0}_phase5_paperlive_results_with_micro.jsonl" -f $Symbol.ToLowerInvariant())

if (-not (Test-Path $in)) { throw "Missing input: $in" }

Write-Host ("[PHASE2-LITE] Symbol={0} in={1} out={2}" -f $Symbol,$in,$out) -ForegroundColor Cyan
& $py (Join-Path $repoRoot "tools\phase2_lite_micro_score.py") $in $out
exit $LASTEXITCODE