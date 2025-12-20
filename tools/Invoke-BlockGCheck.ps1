[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1") | Out-Host
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Check-BlockGReady.ps1") -Symbol $Symbol
exit $LASTEXITCODE