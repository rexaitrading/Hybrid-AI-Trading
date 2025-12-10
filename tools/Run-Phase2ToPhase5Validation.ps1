[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $PSCommandPath
$repoRoot  = Split-Path -Parent $scriptDir

if (-not (Test-Path $repoRoot)) {
    throw "[PHASE2-5] Repo root not found from script path: $repoRoot"
}

Push-Location $repoRoot
try {
    Write-Host "`n[PHASE2-5] Phase-2 → Phase-5 validation suite starting..." -ForegroundColor Cyan
    Write-Host "[PHASE2-5] RepoRoot = $repoRoot" -ForegroundColor DarkCyan

    # Step 1: SPY/QQQ microstructure enrichment
    if (Test-Path '.\tools\spy_qqq_microstructure_enrich.py') {
        $PythonExe = ".\.venv\Scripts\python.exe"
        if (-not (Test-Path $PythonExe)) {
            throw "[PHASE2-5] Python exe not found at $PythonExe"
        }

        Write-Host "`n[PHASE2-5] Running spy_qqq_microstructure_enrich.py..." -ForegroundColor Yellow
        & $PythonExe .\tools\spy_qqq_microstructure_enrich.py
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            Write-Host "[ERROR] spy_qqq_microstructure_enrich.py exit code = $exitCode" -ForegroundColor Red
        }
    } else {
        Write-Host "[WARN] tools\spy_qqq_microstructure_enrich.py not found; skipping enrichment." -ForegroundColor Yellow
    }

    # Step 2: Phase-5 tests (risk + engine)
    if (Test-Path '.\tools\Run-Phase5Tests.ps1') {
        Write-Host "`n[PHASE2-5] Running Run-Phase5Tests.ps1..." -ForegroundColor Yellow
        .\tools\Run-Phase5Tests.ps1
    } else {
        Write-Host "[WARN] Run-Phase5Tests.ps1 not found; invoke pytest manually for Phase-5 tests." -ForegroundColor Yellow
    }

    # Step 3: Quick cost vs EV-band sanity from spy_qqq_micro_for_notion.csv
    $microCsv = Join-Path $repoRoot 'logs\spy_qqq_micro_for_notion.csv'
    if (Test-Path $microCsv) {
        Write-Host "`n[PHASE2-5] Sample of spy_qqq_micro_for_notion.csv (cost vs microstructure)" -ForegroundColor Yellow
        Import-Csv $microCsv | Select-Object -First 10 symbol, ms_range_pct, ms_trend_flag, est_spread_bps, est_fee_bps | Format-Table -AutoSize
    } else {
        Write-Host "[WARN] logs\spy_qqq_micro_for_notion.csv not found; cannot show cost sample." -ForegroundColor Yellow
    }

    Write-Host "`n[PHASE2-5] Phase-2 → Phase-5 validation suite complete." -ForegroundColor Cyan
}
finally {
    Pop-Location
}