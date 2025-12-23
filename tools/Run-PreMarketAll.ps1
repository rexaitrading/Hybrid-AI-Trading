[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "[PRE] RepoRoot=$repoRoot" -ForegroundColor Cyan

# 1) Sweep (fast health)
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-PhaseSweep7.ps1")
if ($LASTEXITCODE -ne 0) { throw "[PRE] Phase sweep failed rc=$LASTEXITCODE" }

# 2) Daily producers (evidence + required slices + contract build)
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-DailyProducersSuite.ps1")
if ($LASTEXITCODE -ne 0) { throw "[PRE] Daily producers failed rc=$LASTEXITCODE" }

# 3) BlockG check (fail-closed)
# 3) BlockG build + check (fail-closed, deterministic)
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1") | Out-Host
if ($LASTEXITCODE -ne 0) { throw "[PRE] BlockG build failed rc=$LASTEXITCODE" }

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Check-BlockGReady.ps1") -Symbol $Symbol | Out-Host$rc = $LASTEXITCODE
Write-Host "[PRE] BlockG RC=$rc" -ForegroundColor Yellow
if ($rc -ne 0) { throw "[PRE] BlockG NOT READY rc=$rc (fail-closed)" }

# 4) Intel (must not break)
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Run-IntelPipeline.ps1")
if ($LASTEXITCODE -ne 0) { throw "[PRE] Intel pipeline failed rc=$LASTEXITCODE" }

Write-Host "[PRE] DONE [OK]" -ForegroundColor Green
exit 0