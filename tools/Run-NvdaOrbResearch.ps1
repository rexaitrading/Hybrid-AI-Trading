[CmdletBinding()]
param(
    [string]$DateTag = (Get-Date -Format 'yyyyMMdd'),
    [string]$NvdaCsv = 'data\NVDA_1m.csv',
    [string]$ReplayOutDir = 'replay_out',
    [string]$ChartsRoot = 'charts',
    [string]$ResearchRoot = 'research'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Resolve repo root from script location
$scriptRoot = $PSScriptRoot
$repoRoot   = Split-Path -Parent $scriptRoot
Set-Location $repoRoot

Write-Host "=== Run-NvdaOrbResearch.ps1 ===" -ForegroundColor Cyan
Write-Host "Repo      : $repoRoot"
Write-Host "DateTag   : $DateTag"
Write-Host "NVDA CSV  : $NvdaCsv"
Write-Host ""

# Python env
$py = '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
    throw "Python not found: $py"
}

# Make src importable
$srcPath = Join-Path $repoRoot 'src'
$env:PYTHONPATH = $srcPath

# Ensure directories exist
foreach ($d in @($ReplayOutDir, $ChartsRoot, $ResearchRoot)) {
    if (-not (Test-Path $d)) {
        New-Item -Path $d -ItemType Directory | Out-Null
        Write-Host "Created directory: $d" -ForegroundColor Green
    }
}

# Paths for this run
$simJson       = Join-Path $ReplayOutDir ("nvda_bplus_trades_{0}.jsonl" -f $DateTag)
$enrichedJson  = Join-Path $ReplayOutDir ("nvda_bplus_trades_{0}_enriched.jsonl" -f $DateTag)
$chartsDir     = Join-Path $ChartsRoot ("NVDA_BPLUS_{0}" -f $DateTag)
$statsCsv      = Join-Path $ResearchRoot ("nvda_bplus_stats_{0}.csv" -f $DateTag)

# Ensure charts subdir exists
if (-not (Test-Path $chartsDir)) {
    New-Item -Path $chartsDir -ItemType Directory | Out-Null
    Write-Host "Created charts directory: $chartsDir" -ForegroundColor Green
}

Write-Host "Sim JSONL      : $simJson"
Write-Host "Enriched JSONL : $enrichedJson"
Write-Host "Charts dir     : $chartsDir"
Write-Host "Stats CSV      : $statsCsv"
Write-Host ""

# 1) NVDA B+ replay sim (offline, no brokers)
Write-Host "[STEP 1] NVDA B+ replay sim -> $simJson" -ForegroundColor Cyan
& $py tools\sim_nvda_bplus_replay.py `
    --csv $NvdaCsv `
    --out $simJson
if ($LASTEXITCODE -ne 0) {
    throw "sim_nvda_bplus_replay.py failed (exit=$LASTEXITCODE)"
}

if (-not (Test-Path $simJson)) {
    throw "Expected sim JSONL not found: $simJson"
}

# 2) Enrich replay JSONL
Write-Host "[STEP 2] Enrich NVDA B+ replay JSONL -> $enrichedJson" -ForegroundColor Cyan
& $py tools\nvda_bplus_enrich_replay_jsonl.py `
    --input $simJson `
    --output $enrichedJson
if ($LASTEXITCODE -ne 0) {
    throw "nvda_bplus_enrich_replay_jsonl.py failed (exit=$LASTEXITCODE)"
}

if (-not (Test-Path $enrichedJson)) {
    throw "Expected enriched JSONL not found: $enrichedJson"
}

# 3) Threshold sweep on gate_score_v2 / EV
Write-Host "[STEP 3] Threshold sweep on gate_score_v2 / EV" -ForegroundColor Cyan
& $py tools\nvda_bplus_threshold_sweep.py `
    --jsonl $enrichedJson `
    --limit 0 `
    --start -0.10 `
    --stop 0.20 `
    --step 0.02
if ($LASTEXITCODE -ne 0) {
    throw "nvda_bplus_threshold_sweep.py failed (exit=$LASTEXITCODE)"
}

# 4) Generate charts
Write-Host "[STEP 4] Generate NVDA B+ charts -> $chartsDir" -ForegroundColor Cyan
& $py tools\nvda_bplus_generate_charts.py `
    --jsonl $enrichedJson `
    --charts-dir $chartsDir `
    --overwrite
if ($LASTEXITCODE -ne 0) {
    throw "nvda_bplus_generate_charts.py failed (exit=$LASTEXITCODE)"
}

# 5) Text replay report
Write-Host "[STEP 5] NVDA B+ replay report" -ForegroundColor Cyan
& $py tools\nvda_bplus_replay_report.py `
    --jsonl $enrichedJson
if ($LASTEXITCODE -ne 0) {
    throw "nvda_bplus_replay_report.py failed (exit=$LASTEXITCODE)"
}

# 6) Stats CSV
Write-Host "[STEP 6] NVDA B+ stats CSV -> $statsCsv" -ForegroundColor Cyan
& $py tools\nvda_bplus_stats.py `
    --jsonl $enrichedJson `
    --out-csv $statsCsv
if ($LASTEXITCODE -ne 0) {
    throw "nvda_bplus_stats.py failed (exit=$LASTEXITCODE)"
}

Write-Host ""
Write-Host "[DONE] Run-NvdaOrbResearch.ps1 completed for DateTag=$DateTag" -ForegroundColor Green
Write-Host "Sim JSONL      : $simJson"
Write-Host "Enriched JSONL : $enrichedJson"
Write-Host "Charts dir     : $chartsDir"
Write-Host "Stats CSV      : $statsCsv"