[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[PREMARKET] NVDA pre-market one-tap STUB (Phase-5 safety branch)" -ForegroundColor Cyan
Write-Host "[PREMARKET] RepoRoot = $repoRoot" -ForegroundColor DarkCyan

# Optional: ensure PYTHONPATH is set (many tools assume src on sys.path)
$env:PYTHONPATH = Join-Path $repoRoot 'src'
Write-Host "[PREMARKET] PYTHONPATH = $env:PYTHONPATH" -ForegroundColor DarkCyan

# 1) Phase-2 -> Phase-5 validation (SPY/QQQ microstructure + Phase-5 tests)
if (Test-Path '.\tools\Run-Phase2ToPhase5Validation.ps1') {
    Write-Host "`n[PREMARKET] Step 1: Run-Phase2ToPhase5Validation.ps1" -ForegroundColor Yellow
    .\tools\Run-Phase2ToPhase5Validation.ps1
} else {
    Write-Host "[PREMARKET] WARN: tools\Run-Phase2ToPhase5Validation.ps1 not found; skipping Phase-2→5 validation." -ForegroundColor Yellow
}

# 2) GateScore daily pipeline
if (Test-Path '.\tools\Run-Phase3GateScoreDaily.ps1') {
    Write-Host "`n[PREMARKET] Step 2: Run-Phase3GateScoreDaily.ps1" -ForegroundColor Yellow
    .\tools\Run-Phase3GateScoreDaily.ps1
} else {
    Write-Host "[PREMARKET] WARN: tools\Run-Phase3GateScoreDaily.ps1 not found; skipping GateScore daily pipeline." -ForegroundColor Yellow
}

# 3) Block-G readiness pipeline
if (Test-Path '.\tools\Run-BlockGReadiness.ps1') {
    Write-Host "`n[PREMARKET] Step 3: Run-BlockGReadiness.ps1" -ForegroundColor Yellow
    .\tools\Run-BlockGReadiness.ps1
} else {
    Write-Host "[PREMARKET] WARN: tools\Run-BlockGReadiness.ps1 not found; skipping Block-G readiness pipeline." -ForegroundColor Yellow
}

Write-Host "`n[PREMARKET] NVDA pre-market one-tap STUB complete." -ForegroundColor Cyan
Write-Host "[PREMARKET] NOTE: This is a safety-branch stub; full live pre-market wiring is not yet implemented." -ForegroundColor DarkYellow