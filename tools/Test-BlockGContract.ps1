[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [switch]$ExitWithCode
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = $PSScriptRoot
$checker  = Join-Path $toolsDir "Check-BlockGReady.ps1"

powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $Symbol
$code = $LASTEXITCODE

Write-Host "[WRAPPER] checker_exitcode=$code" -ForegroundColor DarkGray

if ($ExitWithCode) { exit $code }