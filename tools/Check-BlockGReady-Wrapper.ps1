[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptPath = $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($scriptPath)) {
  throw "[WRAPPER] Cannot resolve script path (MyInvocation). Run this wrapper as a file."
}

$toolsDir = Split-Path -Parent $scriptPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

& (Join-Path $toolsDir "Check-BlockGReady.ps1") -Symbol $Symbol
exit $LASTEXITCODE