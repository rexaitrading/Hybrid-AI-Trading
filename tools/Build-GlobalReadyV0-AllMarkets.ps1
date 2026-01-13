[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

$Markets = @("US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ")
$prods = @(
  "tools\Build-MarketDNA.ps1",
  "tools\Build-EdgeValidity.ps1",
  "tools\Build-DependencyRisk.ps1",
  "tools\Build-RiskGuardStatus.ps1"
)

foreach($m in $Markets){
  foreach($rel in $prods){
    $p = Join-Path $repoRoot $rel
    if(-not (Test-Path -LiteralPath $p)){ throw "Missing producer: $p" }
    & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $p -Market $m | Out-Null
  }
}

Write-Host "[GlobalReadyV0] wrote G1-G4 artifacts for all markets (policy still fail-closed)" -ForegroundColor Green
