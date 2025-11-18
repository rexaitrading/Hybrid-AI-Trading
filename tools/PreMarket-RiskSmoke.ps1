[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$toolsDir = $PSScriptRoot
$repoRoot = (Get-Item $toolsDir).Parent.FullName

Write-Host "[RiskSmoke] repoRoot = $repoRoot" -ForegroundColor Cyan
Set-Location $repoRoot

# Activate venv
$activate = Join-Path $repoRoot '.venv\Scripts\Activate.ps1'
if (Test-Path $activate) {
    Write-Host "[RiskSmoke] Activating venv via $activate" -ForegroundColor Cyan
    & $activate
}

# Set PYTHONPATH
$setPy = Join-Path $toolsDir 'Set-PythonPath.ps1'
if (Test-Path $setPy) {
    Write-Host "[RiskSmoke] Setting PYTHONPATH via $setPy" -ForegroundColor Cyan
    & $setPy
}

# Smoke config and tests
$testTarget  = 'tests/test_risk_halts.py'
$smokeConfig = Join-Path $toolsDir 'pytest_smoke.ini'

if (-not (Test-Path $testTarget)) {
    Write-Host "[RiskSmoke] Test target not found: $testTarget" -ForegroundColor Yellow
    Write-Host "[RiskSmoke] Adjust PreMarket-RiskSmoke.ps1 to point to your real risk smoke suite." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $smokeConfig)) {
    Write-Host "[RiskSmoke] Smoke config not found: $smokeConfig" -ForegroundColor Yellow
    Write-Host "[RiskSmoke] Create tools\pytest_smoke.ini before running RiskSmoke." -ForegroundColor Yellow
    exit 1
}

# Prefer the pytest.exe in venv if available
$pytestExe = Join-Path $repoRoot '.venv\Scripts\pytest.exe'

if (Test-Path $pytestExe) {
    Write-Host "[RiskSmoke] Running $pytestExe -c $smokeConfig -q $testTarget" -ForegroundColor Cyan
    & $pytestExe -c $smokeConfig -q $testTarget
} else {
    Write-Host "[RiskSmoke] pytest.exe not found, falling back to python -m pytest" -ForegroundColor Yellow
    python -m pytest -c $smokeConfig -q $testTarget
}

$code = $LASTEXITCODE

if ($code -ne 0) {
    Write-Host "[RiskSmoke] Risk smoke tests FAILED with exit code $code" -ForegroundColor Red
    exit $code
}

Write-Host "[RiskSmoke] Risk smoke tests PASSED" -ForegroundColor Green
exit 0