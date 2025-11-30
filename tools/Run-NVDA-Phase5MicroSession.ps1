$ErrorActionPreference = "Stop"

# Resolve repo root from tools\ path
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host ""
Write-Host "[NVDA] Phase-5 micro session (LIVE entry -> EXIT demo -> audit)" -ForegroundColor Cyan

$PythonExe      = ".\.venv\Scripts\python.exe"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")

# 1) LIVE-STYLE ENTRY (paper)
Write-Host ""
Write-Host "[NVDA] Step 1/3 - live-paper entry via nvda_phase5_live_smoke.py" -ForegroundColor Yellow
& $PythonExe "tools\nvda_phase5_live_smoke.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] nvda_phase5_live_smoke.py exited with code $LASTEXITCODE - aborting micro-session." -ForegroundColor Red
    exit $LASTEXITCODE
}

# 2) PAPER EXIT DEMO (logs realized PnL into nvda_phase5_paperlive_results.jsonl)
Write-Host ""
Write-Host "[NVDA] Step 2/3 - paper EXIT demo via nvda_phase5_paper_exit_demo.py" -ForegroundColor Yellow
& $PythonExe "tools\nvda_phase5_paper_exit_demo.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] nvda_phase5_paper_exit_demo.py exited with code $LASTEXITCODE - aborting micro-session." -ForegroundColor Red
    exit $LASTEXITCODE
}

# 3) FULL PHASE-5 AUDIT (NVDA + SPY + QQQ)
Write-Host ""
Write-Host "[NVDA] Step 3/3 - running Phase-5 audit (NVDA + SPY + QQQ)" -ForegroundColor Yellow
& ".\tools\Run-Phase5Audit.ps1"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Run-Phase5Audit.ps1 exited with code $LASTEXITCODE" -ForegroundColor DarkYellow
} else {
    Write-Host ""
    Write-Host "[NVDA] Phase-5 micro session complete." -ForegroundColor Green
}
