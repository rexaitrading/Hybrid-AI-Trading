param(
    [string]$PythonExeOverride
)

$ErrorActionPreference = 'Stop'

# Determine repo root from this script's location
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path    # ...\HybridAITrading\tools
$repoRoot  = Split-Path $scriptDir -Parent                      # ...\HybridAITrading

Set-Location $repoRoot

if ($PythonExeOverride) {
    $PythonExe = $PythonExeOverride
} else {
    $PythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
}

Write-Host ''
Write-Host "[PHASE5] Multi-symbol Phase-5 orchestration starting..." -ForegroundColor Cyan
Write-Host "[PHASE5] Using PythonExe = $PythonExe" -ForegroundColor Cyan

if (-not (Test-Path $PythonExe)) {
    Write-Host "[PHASE5] ERROR: Python exe not found at $PythonExe" -ForegroundColor Red
    exit 1
}

# 1) Rebuild Phase-5 decisions from replay (SPY)
Write-Host ''
Write-Host "[STEP 1] Rebuilding Phase-5 decisions from replay..." -ForegroundColor Yellow
& $PythonExe tools/rebuild_phase5_decisions_from_replay.py --symbol SPY --input logs/spy_phase5_replay_gated.jsonl --output logs/spy_phase5_decisions.json

# 2) Run mock Phase-5 NVDA
Write-Host ''
Write-Host "[STEP 2] NVDA Phase-5 mock runner..." -ForegroundColor Yellow
if (Test-Path 'tools\mock_phase5_nvda_runner.py') {
    & $PythonExe tools/mock_phase5_nvda_runner.py
} else {
    Write-Host "  (mock_phase5_nvda_runner.py not found, skipping NVDA runner)" -ForegroundColor DarkYellow
}

# 3) Run mock Phase-5 SPY
Write-Host ''
Write-Host "[STEP 3] SPY ORB Phase-5 mock runner..." -ForegroundColor Yellow
if (Test-Path 'tools\mock_phase5_spy_orb_runner.py') {
    & $PythonExe tools/mock_phase5_spy_orb_runner.py
} else {
    Write-Host "  (mock_phase5_spy_orb_runner.py not found, skipping SPY runner)" -ForegroundColor DarkYellow
}

# 4) Run mock Phase-5 QQQ
Write-Host ''
Write-Host "[STEP 4] QQQ ORB Phase-5 mock runner..." -ForegroundColor Yellow
if (Test-Path 'tools\mock_phase5_qqq_orb_runner.py') {
    & $PythonExe tools/mock_phase5_qqq_orb_runner.py
} else {
    Write-Host "  (mock_phase5_qqq_orb_runner.py not found, skipping QQQ runner)" -ForegroundColor DarkYellow
}

# 5) Export SPY ORB to CSV for Notion
Write-Host ''
Write-Host "[STEP 5] Export SPY ORB enriched trades to CSV for Notion..." -ForegroundColor Yellow
if (Test-Path 'tools\spy_orb_decisions_to_csv.py') {
    & $PythonExe tools/spy_orb_decisions_to_csv.py
} else {
    Write-Host "  (spy_orb_decisions_to_csv.py not found, skipping SPY CSV export)" -ForegroundColor DarkYellow
}

# 6) Export QQQ ORB to CSV for Notion
Write-Host ''
Write-Host "[STEP 6] Export QQQ ORB enriched trades to CSV for Notion..." -ForegroundColor Yellow
if (Test-Path 'tools\qqq_orb_decisions_to_csv.py') {
    & $PythonExe tools/qqq_orb_decisions_to_csv.py
} else {
    Write-Host "  (qqq_orb_decisions_to_csv.py not found, skipping QQQ CSV export)" -ForegroundColor DarkYellow
}

# 7) Multi-symbol per-day summary
Write-Host ''
Write-Host "[STEP 7] Unified NVDA/SPY/QQQ Phase-5 per-day summary..." -ForegroundColor Yellow
if (Test-Path 'tools\phase5_summary_multi.py') {
    & $PythonExe tools/phase5_summary_multi.py
} else {
    Write-Host "  (phase5_summary_multi.py not found, skipping unified summary)" -ForegroundColor DarkYellow
}

Write-Host ''
Write-Host "[PHASE5] Multi-symbol Phase-5 orchestration completed." -ForegroundColor Green