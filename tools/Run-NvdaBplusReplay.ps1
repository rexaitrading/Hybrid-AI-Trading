[CmdletBinding()]
param(
    # Date tag used only in the output filenames, default = today (UTC)
    [string]$DateTag = (Get-Date -Format 'yyyyMMdd')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# This script lives in tools\, repo root is its parent
$scriptRoot = $PSScriptRoot
$repoRoot   = Split-Path -Parent $scriptRoot

Set-Location $repoRoot

$py       = '.venv\Scripts\python.exe'
$sim      = Join-Path $repoRoot 'tools\sim_nvda_bplus_replay.py'
$enricher = Join-Path $repoRoot 'tools\nvda_bplus_enrich_replay_jsonl.py'
$dataCsv  = Join-Path $repoRoot 'data\NVDA_1m.csv'

if (-not (Test-Path $py))       { throw "Python not found: $py" }
if (-not (Test-Path $sim))      { throw "Sim script not found: $sim" }
if (-not (Test-Path $enricher)) { throw "Enricher script not found: $enricher" }
if (-not (Test-Path $dataCsv))  { throw "NVDA data CSV not found: $dataCsv" }

$replayOut = Join-Path $repoRoot 'replay_out'
if (-not (Test-Path $replayOut)) {
    New-Item -Path $replayOut -ItemType Directory | Out-Null
}

# Filenames: sim output + enriched output
$baseName = "nvda_bplus_trades_${DateTag}.jsonl"
$simOut   = Join-Path $replayOut $baseName
$enriched = Join-Path $replayOut ("{0}_enriched.jsonl" -f [System.IO.Path]::GetFileNameWithoutExtension($baseName))

Write-Host "=== NVDA B+ Replay Runner ===" -ForegroundColor Cyan
Write-Host "Repo       : $repoRoot"
Write-Host "Data CSV   : $dataCsv"
Write-Host "Sim out    : $simOut"
Write-Host "Enriched   : $enriched"
Write-Host ""

# 1) Run sim: NVDA B+ replay (0.7% TP / 0.35% SL)
& $py $sim `
    --csv $dataCsv `
    --symbol 'NVDA' `
    --out $simOut `
    --tp 0.007 `
    --sl 0.0035

# 2) Run enricher on sim output
& $py $enricher `
    --input  $simOut `
    --output $enriched

Write-Host ""
Write-Host "[DONE] NVDA B+ replay + enrich complete." -ForegroundColor Green
Write-Host "Sim JSONL     : $simOut"
Write-Host "Enriched JSONL: $enriched"