param(
    [string]$PythonExe = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Resolve repo root from this script's folder
$repoRoot = Split-Path $PSScriptRoot -Parent
Push-Location $repoRoot
try {
    # Ensure we are in the correct (non-mojibake) path
    Write-Host "[Phase5] Repo root:" (Get-Location) -ForegroundColor DarkCyan

    # Make src/ importable for all Phase-5 tests
    $oldPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = "src"

    Write-Host "`n[Phase5] Step 1: Test-Phase5Sanity.ps1 ..." -ForegroundColor Cyan
    & "$PSScriptRoot\Test-Phase5Sanity.ps1"

    # Test-Phase5Sanity.ps1 may change the current directory; force it back.
    Set-Location $repoRoot
    Write-Host "[Phase5] CWD after sanity reset to:" (Get-Location) -ForegroundColor DarkCyan

    Write-Host "`n[Phase5] Step 2: Test-Phase5NoAveragingEngineGuard.ps1 ..." -ForegroundColor Cyan
    & "$PSScriptRoot\Test-Phase5NoAveragingEngineGuard.ps1"

    Write-Host "`n[Phase5] Micro suite completed successfully." -ForegroundColor Green
}
finally {
    if ($null -ne $oldPythonPath -and $oldPythonPath -ne "") {
        $env:PYTHONPATH = $oldPythonPath
    } else {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    }
    Pop-Location
}