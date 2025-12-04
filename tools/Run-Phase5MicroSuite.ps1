$ErrorActionPreference = "Stop"

# scriptDir = tools/, repoRoot = parent of tools (actual repo root)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
Set-Location $repoRoot

$PythonExe = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[CI] Python venv not found at $PythonExe" -ForegroundColor Red
    exit 1
}

# Ensure src/ is on PYTHONPATH for tests
$env:PYTHONPATH = Join-Path $repoRoot "src"

$ciListPath = Join-Path $repoRoot "config\phase5\ci_microsuite.txt"
if (-not (Test-Path $ciListPath)) {
    Write-Host "[CI] Test list not found: $ciListPath" -ForegroundColor Red
    exit 1
}

Write-Host "`n[CI] Running Phase-5 microsuite from $ciListPath" -ForegroundColor Cyan

# Read tests, ignore blank lines and comments starting with '#'
$tests = Get-Content $ciListPath | Where-Object { $_ -and -not $_.Trim().StartsWith("#") }

if (-not $tests -or $tests.Count -eq 0) {
    Write-Host "[CI] No tests found in $ciListPath" -ForegroundColor Red
    exit 1
}

foreach ($t in $tests) {
    Write-Host "`n[CI] pytest $t" -ForegroundColor Cyan
    & $PythonExe -m pytest $t
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[CI] FAILED: $t" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host "`n[CI] Phase-5 microsuite PASSED" -ForegroundColor Green