$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
Set-Location $repoRoot

$PythonExe = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[PORTFOLIO] Python venv not found at $PythonExe" -ForegroundColor Red
    exit 1
}

$env:PYTHONPATH = Join-Path $repoRoot "src"

$ciListPath = Join-Path $repoRoot "config\phase5\ci_portfolio_microsuite.txt"
if (-not (Test-Path $ciListPath)) {
    Write-Host "[PORTFOLIO] Test list not found: $ciListPath" -ForegroundColor Red
    exit 1
}

Write-Host "`n[PORTFOLIO] Running portfolio/exec microsuite from $ciListPath" -ForegroundColor Cyan

$tests = Get-Content $ciListPath | Where-Object { $_ -and -not $_.Trim().StartsWith("#") }
if (-not $tests -or $tests.Count -eq 0) {
    Write-Host "[PORTFOLIO] No tests found in $ciListPath" -ForegroundColor Red
    exit 1
}

foreach ($t in $tests) {
    Write-Host "`n[PORTFOLIO] pytest $t" -ForegroundColor Cyan
    & $PythonExe -m pytest $t
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[PORTFOLIO] FAILED: $t" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host "`n[PORTFOLIO] Portfolio/exec microsuite PASSED" -ForegroundColor Green