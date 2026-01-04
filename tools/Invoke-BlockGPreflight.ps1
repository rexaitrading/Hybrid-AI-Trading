[CmdletBinding()]
param(
    [ValidateSet("NVDA","SPY","QQQ","ALL")]
    [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-BlockGStatusStub.ps1 -Symbol ALL | Out-Host
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Check-BlockGDiagnosticOk.ps1 -Symbol $Symbol | Out-Host

if ($LASTEXITCODE -ne 0) {
    throw "BLOCK-G preflight failed for $Symbol (fail-closed)."
}

Write-Host "BLOCK-G preflight OK for $Symbol ✅" -ForegroundColor Green
exit 0
