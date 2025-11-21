[CmdletBinding()]
param(
    [string]$DateTag = (Get-Date -Format 'yyyyMMdd'),
    [string]$ReplayOutDir = 'replay_out',
    [string]$ResearchRoot = 'research'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptRoot = $PSScriptRoot
$repoRoot   = Split-Path -Parent $scriptRoot
Set-Location $repoRoot

Write-Host "=== Run-QqqOrbResearch.ps1 ===" -ForegroundColor Cyan
Write-Host "Repo      : $repoRoot"
Write-Host "DateTag   : $DateTag"
Write-Host ""

$py = '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
    throw "Python not found: $py"
}

$srcPath = Join-Path $repoRoot 'src'
$env:PYTHONPATH = $srcPath

if (-not (Test-Path $ResearchRoot)) {
    New-Item -Path $ResearchRoot -ItemType Directory | Out-Null
    Write-Host "Created directory: $ResearchRoot" -ForegroundColor Green
}

$qqqJson = Join-Path $ReplayOutDir ("qqq_orb_trades_{0}_orb5_tp2.5.jsonl" -f $DateTag)
if (-not (Test-Path $qqqJson)) {
    throw "[Run-QqqOrbResearch] ORB JSONL not found: $qqqJson. Run Run-Phase5WithGuards.ps1 first."
}

$evTxt = Join-Path $ResearchRoot ("qqq_orb_ev_threshold_sweep_{0}.txt" -f $DateTag)
$evPng = Join-Path $ResearchRoot ("qqq_orb_ev_by_orb_window_{0}.png" -f $DateTag)

Write-Host "QQQ ORB JSONL : $qqqJson"
Write-Host "EV sweep TXT  : $evTxt"
Write-Host "EV plot PNG   : $evPng"
Write-Host ""

# 1) EV vs GateScore edge_ratio sweep
Write-Host "[STEP 1] QQQ ORB EV sweep (GateScore edge_ratio) -> $evTxt" -ForegroundColor Cyan
& $py tools\qqq_orb_ev_threshold_sweep.py `
    --jsonl $qqqJson `
    --start -0.10 `
    --stop 0.20 `
    --step 0.02 | Tee-Object -FilePath $evTxt
if ($LASTEXITCODE -ne 0) {
    throw "qqq_orb_ev_threshold_sweep.py failed (exit=$LASTEXITCODE)"
}

# 2) Plot EV vs ORB window (reuse plot_spy_orb_ev.py for QQQ)
Write-Host "[STEP 2] Plot QQQ ORB EV by ORB window -> $evPng" -ForegroundColor Cyan
& $py tools\plot_spy_orb_ev.py `
    --txt $evTxt `
    --out $evPng
if ($LASTEXITCODE -ne 0) {
    throw "plot_spy_orb_ev.py failed (exit=$LASTEXITCODE)"
}

# 3) GateScore analysis on QQQ ORB JSONL
Write-Host "[STEP 3] Analyze ORB GateScore for QQQ -> console" -ForegroundColor Cyan
& $py tools\analyze_orb_gatescore.py `
    --jsonl $qqqJson
if ($LASTEXITCODE -ne 0) {
    throw "analyze_orb_gatescore.py failed (exit=$LASTEXITCODE)"
}

Write-Host ""
Write-Host "[DONE] Run-QqqOrbResearch.ps1 completed for DateTag=$DateTag" -ForegroundColor Green
Write-Host "QQQ ORB JSONL : $qqqJson"
Write-Host "EV sweep TXT  : $evTxt"
Write-Host "EV plot PNG   : $evPng"