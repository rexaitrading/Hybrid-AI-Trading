[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
$env:HAT_IS_PAPER = "1"


$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

function Run-Tool([string]$name){
  $p = Join-Path $toolsDir $name
  if(-not (Test-Path -LiteralPath $p)){ throw "Missing tool: $p" }
  powershell -NoProfile -ExecutionPolicy Bypass -File $p | Out-Host
  if($LASTEXITCODE -ne 0){ throw "Tool failed rc=$LASTEXITCODE : $name" }
}

Run-Tool "Run-Phase23HealthDaily.ps1"
Run-Tool "Run-EvHardVetoDaily.ps1"
Run-Tool "Run-BuildGateScoreSummaries.ps1"

Remove-Item Env:HAT_BLOCKG_BUILT_ONCE -ErrorAction SilentlyContinue
$env:HAT_BLOCKG_BUILT_ONCE = "0"
Run-Tool "Build-BlockGStatusStub.ps1"

Write-Host "[STAMP-ALL] OK" -ForegroundColor Cyan
exit 0
