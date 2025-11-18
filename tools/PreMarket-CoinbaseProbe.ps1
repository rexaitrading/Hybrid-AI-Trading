[CmdletBinding()]
param(
    [string]$RepoPath,
    [switch]$VerboseOut
)

$ErrorActionPreference = 'Stop'

function Write-Info {
    param([string]$Message)
    Write-Host "[PreMarket-CoinbaseProbe] $Message"
}

# Infer repo root from this script if not supplied
if (-not $RepoPath) {
    # $PSScriptRoot = ...\HybridAITrading\tools
    $RepoPath = Split-Path -Parent $PSScriptRoot
}

if (-not (Test-Path $RepoPath)) {
    throw "Repo path not found: $RepoPath"
}

Set-Location $RepoPath
Write-Info "Repo: $RepoPath"

# Compute tool paths explicitly
$toolsDir = Join-Path $RepoPath 'tools'
$setPy    = Join-Path $toolsDir 'Set-PythonPath.ps1'
$probe    = Join-Path $toolsDir 'Probe-Coinbase.ps1'

# Activate venv if available
$activate = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $activate) {
    Write-Info "Activating venv via $activate"
    & $activate
} else {
    Write-Info "Venv activator not found at $activate; assuming venv is already active."
}

# Ensure PYTHONPATH is set for src layout
if (-not (Test-Path $setPy)) {
    throw "Set-PythonPath script not found at $setPy"
}
Write-Info "Setting PYTHONPATH via $setPy"
& $setPy | Out-Null

# Run the main Coinbase probe
if (-not (Test-Path $probe)) {
    throw "Probe-Coinbase script not found at $probe"
}

Write-Info "Running $probe"
if ($VerboseOut) {
    & $probe
} else {
    # Capture and echo minimal output
    $out = & $probe 2>&1
    $out | Where-Object { $_ -match 'Probe-Coinbase|\bREQUEST URI\b|\bSTATUS\b|\bBODY\b' } |
        ForEach-Object { Write-Host $_ }
}

Write-Info "Pre-market Coinbase probe completed."