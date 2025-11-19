param(
    [int]$Limit = 0,
    [int]$TopN  = 10
)

# Derive repo root based on this script's location (no hard-coded Chinese path)
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot   = Split-Path $scriptRoot -Parent

Set-Location $repoRoot
$ErrorActionPreference = 'Stop'

$nvdaJsonl = Join-Path $repoRoot 'research\nvda_bplus_replay_trades.jsonl'

Write-Host "=== NVDA B+ Analytics Runner ===" -ForegroundColor Cyan
Write-Host "[SCRIPT ROOT] $scriptRoot"
Write-Host "[REPO ROOT]   $repoRoot"
Write-Host "[JSONL]       $nvdaJsonl"
Write-Host "[ARGS]        Limit=$Limit TopN=$TopN"
Write-Host ""

if (-not (Test-Path $nvdaJsonl)) {
    Write-Error "NVDA JSONL not found: $nvdaJsonl"
    exit 1
}

# STEP 1: Threshold sweep (GateScore vs EV)
Write-Host ">>> STEP 1: GateScore threshold sweep <<<" -ForegroundColor DarkCyan
python tools\nvda_bplus_threshold_sweep.py `
    --jsonl $nvdaJsonl `
    --limit $Limit `
    --start -0.10 `
    --stop 0.20 `
    --step 0.02
Write-Host ""

# STEP 2: Replay summary report (PnL, R, GateScore, EV)
Write-Host ">>> STEP 2: Replay summary report <<<" -ForegroundColor DarkGreen
python tools\nvda_bplus_replay_report.py `
    --jsonl $nvdaJsonl `
    --limit $Limit
Write-Host ""

# STEP 3: Cost probe (per-trade cost in $ and bp)
Write-Host ">>> STEP 3: Cost probe (per-trade) <<<" -ForegroundColor DarkYellow
python tools\Probe-ReplayCostModel.py `
    --jsonl $nvdaJsonl
Write-Host ""

Write-Host "=== NVDA B+ Analytics Runner: Done ===" -ForegroundColor Cyan