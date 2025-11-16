[CmdletBinding()]
param(
    # Input NVDA CSV (timestamp,open,high,low,close,volume)
    [Parameter(Mandatory = $true)]
    [string]$CsvPath,

    # Output JSONL file for trades
    [Parameter(Mandatory = $true)]
    [string]$OutPath,

    # Python executable (defaults to "python"; override if needed)
    [Parameter(Mandatory = $false)]
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Test-Path $CsvPath)) {
    throw "CSV not found: $CsvPath"
}

# Resolve script location so it works from repo root
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$simPath = Join-Path $here "sim_nvda_bplus_replay.py"

if (-not (Test-Path $simPath)) {
    throw "Replay sim not found: $simPath"
}

# Ensure output directory exists
$outDir = Split-Path -Parent $OutPath
if ($outDir -and -not (Test-Path $outDir)) {
    New-Item -Path $outDir -ItemType Directory -Force | Out-Null
}

Write-Host "[Run-NVDA-ReplaySim] Python: $PythonExe" -ForegroundColor Cyan
Write-Host "[Run-NVDA-ReplaySim] CSV:    $CsvPath" -ForegroundColor Cyan
Write-Host "[Run-NVDA-ReplaySim] Out:    $OutPath" -ForegroundColor Cyan

# Build arguments: 0.7% TP / 0.35% SL, NVDA symbol
$arguments = @(
    $simPath,
    "--csv", $CsvPath,
    "--symbol", "NVDA",
    "--out", $OutPath,
    "--tp", "0.7",
    "--sl", "0.35"
)

# Invoke Python
& $PythonExe @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Replay sim failed with exit code $LASTEXITCODE"
}

Write-Host "[Run-NVDA-ReplaySim] Completed OK." -ForegroundColor Green