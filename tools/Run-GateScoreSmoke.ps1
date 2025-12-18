[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$py = Join-Path $repoRoot ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

$Symbol = $Symbol.Trim().ToUpperInvariant()

# Prefer per-symbol smoke script if present
$smokeMap = @{
  "NVDA" = "tools\_nvda_gate_score_smoke.py"
  "SPY"  = "tools\_spy_gate_score_smoke.py"
  "QQQ"  = "tools\_qqq_gate_score_smoke.py"
}

$smoke = $smokeMap[$Symbol]
if (-not $smoke) { $smoke = $smokeMap["NVDA"] }

if (-not (Test-Path $smoke)) {
  # Fallback: if only NVDA smoke exists, allow NVDA; for SPY/QQQ fail-closed
  if ($Symbol -ne "NVDA") {
    Write-Host "[PHASE3-SMOKE] Missing per-symbol smoke script for $Symbol ($smoke). FAIL-CLOSED." -ForegroundColor Yellow
    exit 10
  }
  $smoke = $smokeMap["NVDA"]
}

Write-Host "[PHASE3-SMOKE] GateScore smoke RUN Symbol=$Symbol" -ForegroundColor Cyan
Write-Host "[PHASE3-SMOKE] Running $smoke via $py" -ForegroundColor Cyan

& $py $smoke
exit $LASTEXITCODE