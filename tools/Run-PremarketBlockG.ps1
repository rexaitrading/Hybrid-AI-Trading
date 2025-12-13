[CmdletBinding()]
param(
  [Parameter()][string]$Symbol = "NVDA"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

function Step([string]$label, [scriptblock]$action) {
  Write-Host "`n[PREMARKET] $label" -ForegroundColor Cyan
  & $action
  $code = $LASTEXITCODE
  if ($code -ne 0) {
    Write-Host "[PREMARKET] FAIL: $label (exit=$code)" -ForegroundColor Red
    exit $code
  }
}

$sym = (($Symbol + "")).Trim().ToUpper()
if (-not $sym) { Write-Host "[PREMARKET] FAIL: Symbol empty" -ForegroundColor Red; exit 2 }

Step "GuardSuite (compile + guard/risk tests)" { powershell -NoProfile -ExecutionPolicy Bypass -File tools\Run-GuardSuite.ps1 }

Step "Phase-4 validation" { powershell -NoProfile -ExecutionPolicy Bypass -File tools\Run-Phase4Validation.ps1 }

Step "Build Block-G contract JSON" { powershell -NoProfile -ExecutionPolicy Bypass -File tools\Build-BlockGStatusStub.ps1 }

Step "Check Block-G ready (contract-only) -Symbol $sym" { powershell -NoProfile -ExecutionPolicy Bypass -File tools\Check-BlockGReady.ps1 -Symbol $sym }

Step "Phase-6 readiness stub -Symbol $sym" { powershell -NoProfile -ExecutionPolicy Bypass -File tools\Test-Phase6Readiness.ps1 -Symbol $sym }

Step "Phase-7 readiness stub -Symbol $sym" { powershell -NoProfile -ExecutionPolicy Bypass -File tools\Test-Phase7Readiness.ps1 -Symbol $sym }

Write-Host "`n[PREMARKET] Show RunContext" -ForegroundColor Yellow
powershell -NoProfile -ExecutionPolicy Bypass -File tools\Show-RunContext.ps1

Write-Host "`n[PREMARKET] OK: all checks green." -ForegroundColor Green
exit 0