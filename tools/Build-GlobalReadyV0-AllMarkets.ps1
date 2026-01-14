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

# P53: copy Phase5 paperlive evidence into per-market logs (PAPER-only; fail-closed in LIVE)
$evid = Join-Path $repoRoot "tools\Write-Phase5PaperliveEvidence-PerMarket.ps1"
if(Test-Path -LiteralPath $evid){
  & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $evid -Market ALL -Symbol NVDA | Out-Null
} else {
  throw "Missing producer: $evid"
}

# P53: real per-market Phase3 GateScore generation (uses per-market Phase5 evidence when present)
$ph3 = Join-Path $repoRoot "tools\Run-Phase3GateScoreDaily-AllMarkets.ps1"
if(Test-Path -LiteralPath $ph3){
  & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $ph3 -Symbol NVDA -Mode rewrite -MinEvents 10 | Out-Null
} else {
  throw "Missing producer: $ph3"
}
# P53: seed fail-closed GateScore stubs for missing markets (deterministic; prevents missing-file ambiguity)
$stub = Join-Path $repoRoot "tools\Write-GateScoreStub-MissingMarkets.ps1"
if(Test-Path -LiteralPath $stub){
  & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $stub -Market ALL -Symbol NVDA | Out-Null
} else {
  throw "Missing producer: $stub"
}

Write-Host "[GlobalReadyV0] wrote G1-G4 artifacts for all markets (policy still fail-closed)" -ForegroundColor Green
