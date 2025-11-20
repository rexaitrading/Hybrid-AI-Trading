[CmdletBinding()]
param(
    # Date tag used only in the output filename, default = today (UTC)
    [string]$DateTag = (Get-Date -Format 'yyyyMMdd'),

    # ORB window length in minutes (default 15)
    [int]$OrbMinutes = 15,

    # Take-profit in R multiples (default 2.0)
    [double]$TpR = 2.0
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptRoot = $PSScriptRoot
$repoRoot   = Split-Path -Parent $scriptRoot

Set-Location $repoRoot

$py        = '.venv\Scripts\python.exe'
$dataCsv   = Join-Path $repoRoot 'data\SPY_1m.csv'
$replayOut = Join-Path $repoRoot 'replay_out'

if (-not (Test-Path $py)) {
    throw "Python not found: $py"
}
if (-not (Test-Path $dataCsv)) {
    throw "SPY data CSV not found: $dataCsv"
}

if (-not (Test-Path $replayOut)) {
    New-Item -Path $replayOut -ItemType Directory | Out-Null
}

# Standardized JSONL output path
$simOut = Join-Path $replayOut ("spy_orb_trades_{0}_orb{1}_tp{2}.jsonl" -f $DateTag, $OrbMinutes, $TpR)

# Convert DateTag (yyyyMMdd) to YYYY-MM-DD for the sim
$dateForSim = [DateTime]::ParseExact($DateTag, 'yyyyMMdd', $null).ToString('yyyy-MM-dd')

# Sim script
$simScript = Join-Path $repoRoot 'tools\spy_orb_phase5_sim.py'

Write-Host "=== SPY ORB Replay (real sim) ===" -ForegroundColor Cyan
Write-Host "Repo       : $repoRoot"
Write-Host "Data       : $dataCsv"
Write-Host "Date       : $dateForSim"
Write-Host "ORB window : $OrbMinutes minute(s)"
Write-Host "TP (R)     : $TpR"
Write-Host "Output     : $simOut"
Write-Host ""

if (-not (Test-Path $simScript)) {
    throw "Sim script not found: $simScript"
}

Write-Host "[INFO] Using sim script: $simScript" -ForegroundColor Green
Write-Host "[INFO] Running SPY ORB sim (RTH) and writing JSONL trades ..." -ForegroundColor Green

# Force Python stdout to UTF-8 (defensive)
$oldIO = $env:PYTHONIOENCODING
$env:PYTHONIOENCODING = 'utf-8'

& $py $simScript `
    --csv $dataCsv `
    --date $dateForSim `
    --symbol 'SPY' `
    --out $simOut `
    --orb-minutes $OrbMinutes `
    --tp-r $TpR

$env:PYTHONIOENCODING = $oldIO

if (-not (Test-Path $simOut)) {
    Write-Host "[WARN] Trade JSONL not created: $simOut" -ForegroundColor Yellow
} else {
    $info = Get-Item $simOut
    Write-Host "[DONE] SPY ORB trade JSONL written." -ForegroundColor Green
    Write-Host ("       {0} bytes  {1}" -f $info.Length, $info.LastWriteTime)
}