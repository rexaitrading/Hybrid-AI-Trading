[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][int]$StubPairs = 1
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$env:PYTHONPATH = Join-Path $repoRoot "src"
$py = Join-Path $repoRoot ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "[PHASE6] Missing python: $py" -ForegroundColor Red; exit 2 }

$base = Join-Path $repoRoot "logs\paper_trades.jsonl"
if (-not (Test-Path $base)) { Write-Host "[PHASE6] FAIL-CLOSED: missing logs\paper_trades.jsonl" -ForegroundColor Red; exit 3 }

# Create stubs into separate file
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Write-SpyQqqPaperStubs.ps1 -Count $StubPairs
if ($LASTEXITCODE -ne 0) { Write-Host "[PHASE6] FAIL stubs writer exit=$LASTEXITCODE" -ForegroundColor Red; exit $LASTEXITCODE }

$stub = Join-Path $repoRoot "logs\paper_trades_spyqqq_stubs.jsonl"
if (-not (Test-Path $stub)) { Write-Host "[PHASE6] FAIL: expected $stub" -ForegroundColor Red; exit 4 }

# Merge into temp (do NOT contaminate base)
$tmp = Join-Path $repoRoot ("logs\paper_trades_core3_tmp_{0}.jsonl" -f (Get-Date).ToString("yyyyMMdd_HHmmss"))
Get-Content $base -Encoding utf8 | Out-File -FilePath $tmp -Encoding utf8
Get-Content $stub -Encoding utf8 | Add-Content -Path $tmp -Encoding utf8

Write-Host "[PHASE6] Using merged temp paper_trades file: $tmp" -ForegroundColor Cyan

# Point strategies to merged file
$env:HAT_PAPER_TRADES_PATH = $tmp

powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-Phase6Core3Paper.ps1
$code = $LASTEXITCODE

# Best-effort cleanup (keep tmp if you want to inspect; comment out to keep always)
# Remove-Item -Force $tmp -ErrorAction SilentlyContinue

exit $code