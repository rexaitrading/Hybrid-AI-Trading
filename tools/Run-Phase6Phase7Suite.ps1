[CmdletBinding()]
param(
  [string]$Symbol = "NVDA",
  [string]$AsOfDate = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

if (-not $AsOfDate) { $AsOfDate = (Get-Date).ToString("yyyy-MM-dd") }

Write-Host "[P6P7] as_of_date=$AsOfDate" -ForegroundColor Cyan

# IMPORTANT: we rely on your existing Daily Producers Suite to refresh:
# EV-hard, Phase4, Phase3, Block-G.
$daily = Join-Path $root "tools\Run-DailyProducersSuite.ps1"
if (-not (Test-Path $daily)) { throw "[P6P7] Missing tools\Run-DailyProducersSuite.ps1" }
& $daily -Symbol $Symbol
if ($LASTEXITCODE -ne 0) { throw "[P6P7] DailyProducersSuite failed exit=$LASTEXITCODE" }

# Phase6
$p6 = Join-Path $root "tools\Run-Phase6DailySummary.ps1"
if (-not (Test-Path $p6)) { throw "[P6P7] Missing $p6" }
& $p6 -AsOfDate $AsOfDate -OutDir "logs\phase6"
if ($LASTEXITCODE -ne 0) { throw "[P6P7] Phase6 failed exit=$LASTEXITCODE" }

# Phase7
$p7 = Join-Path $root "tools\Run-Phase7Optimizer.ps1"
if (-not (Test-Path $p7)) { throw "[P6P7] Missing $p7" }
& $p7 -AsOfDate $AsOfDate -OutDir "logs\phase7" -Symbols "NVDA,SPY,QQQ" -MaxWeight 0.60
if ($LASTEXITCODE -ne 0) { throw "[P6P7] Phase7 failed exit=$LASTEXITCODE" }

Write-Host "[P6P7] DONE ✅ Phase6+Phase7 artifacts written." -ForegroundColor Green
exit 0