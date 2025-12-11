[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "[PHASE2] Phase-2 SPY/QQQ micro + cost snapshot RUN" -ForegroundColor Cyan
Write-Host "[PHASE2] RepoRoot = $repoRoot" -ForegroundColor DarkCyan

$env:PYTHONPATH = Join-Path $repoRoot "src"
$pythonExe      = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "[PHASE2] ERROR: Python executable not found at $pythonExe" -ForegroundColor Red
    exit 1
}

$microScript = Join-Path $repoRoot "tools\spy_qqq_microstructure_enrich.py"
if (-not (Test-Path $microScript)) {
    Write-Host "[PHASE2] WARN: spy_qqq_microstructure_enrich.py not found at $microScript" -ForegroundColor Yellow
} else {
    Write-Host "[PHASE2] Running spy_qqq_microstructure_enrich.py via $pythonExe" -ForegroundColor Yellow
    & $pythonExe $microScript
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        Write-Host "[PHASE2] WARN: spy_qqq_microstructure_enrich.py exit code = $code (non-fatal for snapshot)." -ForegroundColor Yellow
    }
}

# Optional diagnostics: show symbol counts in spy_qqq_micro_for_notion.csv
$logsDir  = Join-Path $repoRoot "logs"
$microCsv = Join-Path $logsDir "spy_qqq_micro_for_notion.csv"

if (Test-Path $microCsv) {
    Write-Host "`n[PHASE2] Symbol distribution in spy_qqq_micro_for_notion.csv" -ForegroundColor Cyan
    Import-Csv $microCsv |
        Group-Object symbol |
        Sort-Object Name |
        Format-Table Name, Count -AutoSize
} else {
    Write-Host "[PHASE2] WARN: spy_qqq_micro_for_notion.csv not found at $microCsv" -ForegroundColor Yellow
}

Write-Host "`n[PHASE2] Phase-2 SPY/QQQ micro snapshot complete (log-only)." -ForegroundColor Green
exit 0