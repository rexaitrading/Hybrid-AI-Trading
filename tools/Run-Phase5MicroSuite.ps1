$ErrorActionPreference = "Stop"

# scriptDir = tools/, repoRoot = parent of tools (actual repo root)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
Set-Location $repoRoot

$PythonExe = ".\.venv\Scripts\python.exe"
$env:PYTHONPATH = Join-Path $repoRoot "src"

$ciListPath = Join-Path $repoRoot "config\phase5\ci_microsuite.txt"

Write-Host "`n[CI] Running Phase-5 microsuite from $ciListPath" -ForegroundColor Cyan

$tests = Get-Content $ciListPath | Where-Object { $_ -and -not $_.StartsWith("#") }

foreach ($t in $tests) {
    Write-Host "`n[CI] pytest $t" -ForegroundColor Cyan
    & $PythonExe -m pytest $t
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[CI] FAILED: $t" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host "`n[CI] Phase-5 microsuite PASSED" -ForegroundColor Green