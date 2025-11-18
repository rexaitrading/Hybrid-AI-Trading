[CmdletBinding()]
param(
    [string]$RepoPath
)

$ErrorActionPreference = 'Stop'

# If RepoPath not supplied, infer repo root from this script's folder:
if (-not $RepoPath) {
    # $PSScriptRoot = ...\HybridAITrading\tools
    $RepoPath = Split-Path -Parent $PSScriptRoot
}

if (-not (Test-Path $RepoPath)) {
    throw "Repo path not found: $RepoPath"
}

Set-Location $RepoPath

$srcRoot = Join-Path $RepoPath 'src'
if (-not (Test-Path $srcRoot)) {
    throw "src folder not found at $srcRoot"
}

$env:PYTHONPATH = $srcRoot

Write-Host "PYTHONPATH set to $env:PYTHONPATH" -ForegroundColor Cyan