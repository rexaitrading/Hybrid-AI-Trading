[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

function Run([string]$p){
  $full = Join-Path $toolsDir $p
  if(-not (Test-Path $full)){ throw "Missing tool: $full" }
  Write-Host ("=== RUN: " + $p + " ===") -ForegroundColor Cyan
  powershell -NoProfile -ExecutionPolicy Bypass -File $full | Out-Host
  if($LASTEXITCODE -ne 0){ throw "$p failed exit=$LASTEXITCODE" }
}

Run "Run-Phase23HealthDaily.ps1"
Run "Run-Phase4Stamp.ps1"
Run "Build-GateScorePnlSummary.ps1"

Run "Build-EvHardEvidenceRaw.ps1"
Run "Build-EvHardSnapshot.ps1"
Run "Compute-Phase5EvHardSnapshotInput.ps1"
Run "Export-Phase5EvHardVetoDailySnapshot.ps1"
Run "Run-EvHardVetoDaily.ps1"

Write-Host ("=== CHECK BLOCKG: " + $Symbol + " (build) ===") -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $toolsDir "Check-BlockGDiagnosticOk.ps1") -Symbol $Symbol | Out-Host
if($LASTEXITCODE -ne 0){ Write-Host "[PH5-SNAPSHOT] FAIL step=blockg_diag rc=$LASTEXITCODE" -ForegroundColor Yellow; exit 91 }
exit $LASTEXITCODE
