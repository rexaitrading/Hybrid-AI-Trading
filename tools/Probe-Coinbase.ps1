# tools\Probe-Coinbase.ps1
# PS 5.1-safe Coinbase Advanced Trade probe for Hybrid AI Trading
# - Optionally activates venv (if activator exists)
# - Loads C:\Secrets\cdp_api_key.json
# - Exports COINBASE_ADV_* env vars
# - Runs adv_jwt_check.py (accounts check)
# - Returns non-zero exit code on failure

[CmdletBinding()]
param(
    [string]$RepoPath,
    [string]$SecretPath  = 'C:\Secrets\cdp_api_key.json',
    [switch]$VerboseOut
)

$ErrorActionPreference = 'Stop'

function Write-Info {
    param([string]$Message)
    Write-Host "[Probe-Coinbase] $Message"
}

Write-Info "Starting Coinbase Advanced Trade probe..."

# 1) Infer RepoPath from this script if not supplied
if (-not $RepoPath) {
    # $PSScriptRoot = ...\HybridAITrading\tools
    $RepoPath = Split-Path -Parent $PSScriptRoot
}

if (-not (Test-Path $RepoPath)) {
    throw "Repo path not found: $RepoPath"
}
Set-Location $RepoPath

# 2) Optionally activate venv if activator exists
$activate = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $activate) {
    Write-Info "Activating venv via $activate"
    & $activate
} else {
    Write-Info "Venv activator not found at $activate; assuming venv is already active."
}

# 3) Ensure key JSON exists (optional copy from Downloads if missing)
if (-not (Test-Path $SecretPath)) {
    $dl  = Join-Path $env:USERPROFILE 'Downloads'
    $src = Get-ChildItem -Path $dl -Filter 'cdp_api_key*.json' -ErrorAction SilentlyContinue |
           Sort-Object LastWriteTime -Descending |
           Select-Object -First 1

    if (-not $src) {
        throw "No cdp_api_key*.json found in $dl and $SecretPath is missing. Download your key JSON first."
    }

    New-Item -ItemType Directory -Path (Split-Path $SecretPath) -ErrorAction SilentlyContinue | Out-Null
    Copy-Item -LiteralPath $src.FullName -Destination $SecretPath -Force
    Write-Info "Copied latest key JSON from Downloads to $SecretPath"
}

# 4) Load JSON -> env vars
$j = Get-Content -Raw -Encoding UTF8 $SecretPath | ConvertFrom-Json

if (-not $j.name -or -not $j.privateKey) {
    throw "Key JSON at $SecretPath missing 'name' or 'privateKey' fields."
}

$env:COINBASE_ADV_KEY_NAME    = $j.name
$env:COINBASE_ADV_PRIVATE_KEY = $j.privateKey

Write-Info ("Loaded KEY NAME: " + $env:COINBASE_ADV_KEY_NAME)

# 5) Sanity check adv_jwt_check.py
$advPath = Join-Path (Get-Location) 'adv_jwt_check.py'
if (-not (Test-Path $advPath)) {
    throw "adv_jwt_check.py not found at $advPath"
}

# 6) Run the Python probe (simple & python, track $LASTEXITCODE)
Write-Info "Running adv_jwt_check.py..."
$LASTEXITCODE = 0
& python .\adv_jwt_check.py
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Error "adv_jwt_check.py exited with code $exitCode"
    exit $exitCode
}

Write-Info "Coinbase probe completed."
exit 0