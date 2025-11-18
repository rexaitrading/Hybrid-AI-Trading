param(
    [switch]$Verbose
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Assume this script lives in scripts/, repo root is one level up
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root      = Split-Path -Parent $scriptDir
Set-Location $root

$replayRunner = Join-Path $root "tools\Run-ReplayMicroSuite.ps1"
if (-not (Test-Path $replayRunner)) {
    throw "Run-ReplayMicroSuite.ps1 not found at $replayRunner"
}

if ($Verbose) {
    & $replayRunner -VerboseOutput
} else {
    & $replayRunner
}
