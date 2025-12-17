[CmdletBinding()]
param()

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$today = (Get-Date).ToString("yyyy-MM-dd")
$env:PYTHONPATH = Join-Path $repoRoot "src"

Write-Host "[PREFLIGHT] repo=$repoRoot today=$today" -ForegroundColor Cyan

# 1) Produce deterministic paperlive + CSV
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Invoke-NvdaPhase5PaperPipeline.ps1

# 2) Build contract
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-BlockGStatusStub.ps1 -Symbol NVDA

# 3) Check readiness (contract-only)
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Check-BlockGReady.ps1 -Symbol NVDA
$code0 = $LASTEXITCODE
if ($code0 -ne 0) {
  Write-Host "[PREFLIGHT] NO-GO exitcode=$code0" -ForegroundColor Red
  exit $code0
}

# 4) Smoke Python enforcement agrees
$py = Join-Path $repoRoot ".\.venv\Scripts\python.exe"
& $py .\tools\smoke\smoke_blockg_contract_enforcement.py
if ($LASTEXITCODE -ne 0) {
  Write-Host "[PREFLIGHT] FAIL: smoke failed" -ForegroundColor Red
  exit 99
}

# 5) Snapshot GO artifact
Copy-Item -Force .\logs\blockg_status_stub.json .\logs\blockg_status_stub_GOOD_LAST.json

Write-Host "[PREFLIGHT] GO: NVDA live allowed (contract + python enforcement)" -ForegroundColor Green
exit 0
