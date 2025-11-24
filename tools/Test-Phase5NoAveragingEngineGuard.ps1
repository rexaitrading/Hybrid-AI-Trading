param(
    [string]$PythonExe = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Repo root = parent of tools\
$repoRoot = Split-Path $PSScriptRoot -Parent
Push-Location $repoRoot

# Save and set PYTHONPATH so hybrid_ai_trading is importable
$oldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = "src"

    Write-Host "[Phase5] Running no-averaging engine-guard tests..." -ForegroundColor Cyan
    & $PythonExe -m pytest "tests/test_phase5_no_averaging_engine_guard.py" -q
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        throw "Phase-5 no-averaging engine-guard tests failed with exit code $exitCode"
    } else {
        Write-Host "[Phase5] No-averaging engine-guard tests PASSED." -ForegroundColor Green
    }
}
finally {
    if ($null -ne $oldPythonPath -and $oldPythonPath -ne "") {
        $env:PYTHONPATH = $oldPythonPath
    } else {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    }
    Pop-Location
}