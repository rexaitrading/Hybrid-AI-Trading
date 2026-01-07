[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol="NVDA",
  [string]$AsOfDate=""  # optional: YYYY-MM-DD
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

# UTF-8 hardening for OneDrive non-ASCII paths (prevents cp1252 UnicodeEncodeError)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $py)){ throw "Missing venv python: $py" }

$today = if($AsOfDate -and $AsOfDate.Trim()){ $AsOfDate.Trim() } else { (Get-Date).ToString("yyyy-MM-dd") }

function Step([string]$name, [scriptblock]$sb){
  "`n====================" | Out-Host
  "STEP: $name" | Out-Host
  "====================" | Out-Host
  & $sb
}

# PH1 — Replay bars integrity (non-interactive)
Step "PH1 bar integrity + session boundaries" {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-BarCompleteness.ps1 -Symbol NVDA *>&1 | Out-Host
  if($LASTEXITCODE -ne 0){ throw "PH1 FAIL: Test-BarCompleteness exit=$LASTEXITCODE" }

  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-SessionBoundaries.ps1 -Symbol NVDA *>&1 | Out-Host
  if($LASTEXITCODE -ne 0){ throw "PH1 FAIL: Test-SessionBoundaries exit=$LASTEXITCODE" }
}

# PH2 — Costs sanity (optional; runs if temp script exists)
Step "PH2 cost sanity" {
  if(Test-Path .\.hat\_tmp_cost_sanity.py){
    & $py .\.hat\_tmp_cost_sanity.py *>&1 | Out-Host
    if($LASTEXITCODE -ne 0){ throw "PH2 FAIL: cost sanity exit=$LASTEXITCODE" }
  } else {
    Write-Host "[PH2] WARN: .\.hat\_tmp_cost_sanity.py not found; skipping" -ForegroundColor Yellow
  }
}

# PH4/PH5 — Guard tests (fast slice; fail-closed)
Step "PH4/PH5 guard tests (fast slice)" {
  & $py -m pytest -q `
    tests/test_phase5_riskmanager_combined_gates.py `
    tests/test_execution_engine_phase5_guard.py `
    tests/test_ib_phase5_guard.py `
    *>&1 | Out-Host
  if($LASTEXITCODE -ne 0){ throw "PH4/PH5 FAIL: pytest slice exit=$LASTEXITCODE" }
}

# PH3/PH4/PH5 — ContractPack (single authority, semantic owner in PS)
Step "PH23->PH4->PH5->PH3 summary->BlockG (ContractPack)" {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-Premarket-ContractPack.ps1 -Symbol $Symbol -AsOfDate $today *>&1 | Out-Host
  if($LASTEXITCODE -ne 0){ throw "ContractPack FAIL: exit=$LASTEXITCODE" }
}

# Final hard requirement: NVDA must be explicitly ready (never infer from ALL)
Step "PH5 BlockG final NVDA readiness" {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Check-BlockGReady.ps1 -Symbol NVDA *>&1 | Out-Host
  if($LASTEXITCODE -ne 0){ throw "BLOCKG FAIL-CLOSED: NVDA not ready exit=$LASTEXITCODE" }
}

Write-Host "`n[OK] Daily PH1-PH5 Upgrade complete - NVDA Live Ready enforced (fail-closed)
exit 0
