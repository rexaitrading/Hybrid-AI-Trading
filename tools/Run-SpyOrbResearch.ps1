[CmdletBinding()]
param(
    [string]$DateTag = (Get-Date -Format 'yyyyMMdd'),
    [string]$ReplayOutDir = 'replay_out',
    [string]$ResearchRoot = 'research'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Resolve repo root
$scriptRoot = $PSScriptRoot
$repoRoot   = Split-Path -Parent $scriptRoot
Set-Location $repoRoot

Write-Host "=== Run-SpyOrbResearch.ps1 ===" -ForegroundColor Cyan
Write-Host "Repo      : $repoRoot"
Write-Host "DateTag   : $DateTag"
Write-Host ""

# Python env
$py = '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
    throw "Python not found: $py"
}

# Make src importable
$srcPath = Join-Path $repoRoot 'src'
$env:PYTHONPATH = $srcPath

# Ensure research dir exists
if (-not (Test-Path $ResearchRoot)) {
    New-Item -Path $ResearchRoot -ItemType Directory | Out-Null
    Write-Host "Created directory: $ResearchRoot" -ForegroundColor Green
}

# ORB JSONL path (produced by your Phase5 multi-strategy runner)
$spyJson = Join-Path $ReplayOutDir ("spy_orb_trades_{0}_orb5_tp2.5.jsonl" -f $DateTag)
if (-not (Test-Path $spyJson)) {
    throw "[Run-SpyOrbResearch] ORB JSONL not found: $spyJson. Run Run-Phase5WithGuards.ps1 first."
}

# Output paths
$evTxt = Join-Path $ResearchRoot ("spy_orb_ev_threshold_sweep_{0}.txt" -f $DateTag)
$evPng = Join-Path $ResearchRoot ("spy_orb_ev_by_orb_window_{0}.png" -f $DateTag)

Write-Host "SPY ORB JSONL : $spyJson"
Write-Host "EV sweep TXT  : $evTxt"
Write-Host "EV plot PNG   : $evPng"
Write-Host ""

# 1) EV vs GateScore edge_ratio sweep (write to console + TXT)
Write-Host "[STEP 1] SPY ORB EV sweep (GateScore edge_ratio) -> $evTxt" -ForegroundColor Cyan
& $py tools\spy_orb_ev_threshold_sweep.py `
    --jsonl $spyJson `
    --start -0.10 `
    --stop 0.20 `
    --step 0.02 | Tee-Object -FilePath $evTxt
if ($LASTEXITCODE -ne 0) {
    throw "spy_orb_ev_threshold_sweep.py failed (exit=$LASTEXITCODE)"
}

# 2) Plot EV vs ORB window
Write-Host "[STEP 2] Plot SPY ORB EV by ORB window -> $evPng" -ForegroundColor Cyan
& $py tools\plot_spy_orb_ev.py `
    --txt $evTxt `
    --out $evPng
if ($LASTEXITCODE -ne 0) {
    throw "plot_spy_orb_ev.py failed (exit=$LASTEXITCODE)"
}

# 3) GateScore analysis on SPY ORB JSONL
Write-Host "[STEP 3] Analyze ORB GateScore for SPY -> console" -ForegroundColor Cyan
& $py tools\analyze_orb_gatescore.py `
    --jsonl $spyJson
if ($LASTEXITCODE -ne 0) {
    throw "analyze_orb_gatescore.py failed (exit=$LASTEXITCODE)"
}

Write-Host ""
Write-Host "[DONE] Run-SpyOrbResearch.ps1 completed for DateTag=$DateTag" -ForegroundColor Green
Write-Host "SPY ORB JSONL : $spyJson"
Write-Host "EV sweep TXT  : $evTxt"
Write-Host "EV plot PNG   : $evPng"