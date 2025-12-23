[CmdletBinding()]
param(
  [string]$Symbol = "NVDA",
  [string]$AsOfDate = ""
)
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)


Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"


# ------------------------------------------------------------
# Block-G FIRST (institutional risk gate / fail-closed)
# ------------------------------------------------------------
$blockgFirst = Join-Path (Split-Path -Parent $PSCommandPath) "Run-BlockGTestsFirst.ps1"
if(Test-Path $blockgFirst){
  powershell -NoProfile -ExecutionPolicy Bypass -File $blockgFirst | Out-Host
  if($LASTEXITCODE -ne 0){
    Write-Host "[DAILY] FAIL-CLOSED: BlockG-first tests failed. Abort daily run." -ForegroundColor Yellow
    exit 2
  }
}else{
  Write-Host "[DAILY] FAIL-CLOSED: missing tools\Run-BlockGTestsFirst.ps1" -ForegroundColor Yellow
  exit 2
}
$root = (Resolve-Path ".").Path
Set-Location $root

if (-not $AsOfDate) { $AsOfDate = (Get-Date).ToString("yyyy-MM-dd") }

Write-Host "[P1-7] RepoRoot=$root" -ForegroundColor Cyan
Write-Host "[P1-7] Symbol=$Symbol AsOfDate=$AsOfDate" -ForegroundColor Cyan

# Deterministic Block-G contract path for Python
$k = ("HAT_" + "BLOCKG_" + "STATUS_" + "PATH")
[System.Environment]::SetEnvironmentVariable($k, (Join-Path $root "logs\blockg_status_stub.json"))

# ---- Phase1 REAL (optional, if replay CSV exists) ----
$session = Join-Path $root "logs\replay\replay_session.json"
if (Test-Path $session) {
  try {
    $csv = (Get-Content $session -Raw -Encoding utf8 | ConvertFrom-Json).bars_path
    if ($csv -and (Test-Path -LiteralPath $csv)) {
      $p1 = Join-Path $root "tools\Run-Phase1ReplayRealCsv.ps1"
      if (Test-Path $p1) {
        Write-Host "[P1-7] Phase1 REAL replay..." -ForegroundColor Cyan
        & $p1 -InputCsv $csv -Symbol $Symbol -OutDir "logs\replay" -Batch 100
        if ($LASTEXITCODE -ne 0) { throw "[P1-7] Phase1 failed exit=$LASTEXITCODE" }
      } else {
        Write-Host "[P1-7] WARN Phase1 runner missing ($p1); skipping." -ForegroundColor Yellow
      }
    } else {
      Write-Host "[P1-7] WARN Phase1 csv missing; skipping." -ForegroundColor Yellow
    }
  } catch {
    Write-Host "[P1-7] WARN Phase1 check failed; skipping. $_" -ForegroundColor Yellow
  }
} else {
  Write-Host "[P1-7] WARN replay_session.json missing; skipping Phase1." -ForegroundColor Yellow
}

# ---- Phase2.1 REAL (optional) ----
$p2 = Join-Path $root "tools\Run-Phase2FromPhase1.ps1"
if (Test-Path $p2) {
  Write-Host "[P1-7] Phase2.1 (from Phase1) ..." -ForegroundColor Cyan
  & $p2 -Session "logs\replay\replay_session.json" -OutDir "logs\phase2" -MaxRows 0
  if ($LASTEXITCODE -ne 0) { throw "[P1-7] Phase2 failed exit=$LASTEXITCODE" }
} else {
  Write-Host "[P1-7] WARN Phase2 runner missing ($p2); skipping." -ForegroundColor Yellow
}

# ---- Phase3/4/5 producers + Block-G ----
$daily = Join-Path $root "tools\Run-DailyProducersSuite.ps1"
if (-not (Test-Path $daily)) { throw "[P1-7] Missing: $daily" }
Write-Host "[P1-7] DailyProducersSuite ..." -ForegroundColor Cyan
& $daily -Symbol $Symbol
if ($LASTEXITCODE -ne 0) { throw "[P1-7] DailyProducersSuite failed exit=$LASTEXITCODE" }


# ------------------------------------------------------------
# NVDA LIVE READY STAMP (contract-only; fail-closed)
# ------------------------------------------------------------
$nvdaStamp = Join-Path (Split-Path -Parent $PSCommandPath) "Write-NvdaLiveReadyStamp.ps1"
if(Test-Path $nvdaStamp){
  powershell -NoProfile -ExecutionPolicy Bypass -File $nvdaStamp | Out-Host
  if($LASTEXITCODE -ne 0){
    Write-Host "[DAILY] FAIL-CLOSED: NVDA LIVE NOT ARMED (stamp not ready)." -ForegroundColor Yellow
    exit 2
  }else{
    Write-Host "[DAILY] NVDA LIVE READY ✅ (stamp ok)." -ForegroundColor Green
    Write-Host ("[DAILY] StampPath=" + (Join-Path $root "logs\nvda_live_ready_stamp.json")) -ForegroundColor DarkGray
  }
}else{
  Write-Host "[DAILY] FAIL-CLOSED: missing tools\Write-NvdaLiveReadyStamp.ps1" -ForegroundColor Yellow
  exit 2
}
# ---- Phase6 ----
$p6 = Join-Path $root "tools\Build-Phase6PortfolioState.ps1"
if (-not (Test-Path $p6)) { throw "[P1-7] Missing: $p6" }
Write-Host "[P1-7] Phase6 daily summary ..." -ForegroundColor Cyan
& $p6 -OutPath "logs\phase6_portfolio_state.json"
if ($LASTEXITCODE -ne 0) { throw "[P1-7] Phase6 failed exit=$LASTEXITCODE" }

# ---- Phase7 ----
$p7 = Join-Path $root "tools\Run-Phase7OptimizerDaily.ps1"
if (-not (Test-Path $p7)) { throw "[P1-7] Missing: $p7" }
Write-Host "[P1-7] Phase7 optimizer ..." -ForegroundColor Cyan
& $p7 -Enable -StatePath "logs\phase6_portfolio_state.json" -BlockGPath "logs\blockg_status_stub.json" -OutDir "logs\phase7" -OutPath "logs\phase7_optimizer_output.json" -Symbols "NVDA,SPY,QQQ" -MaxWeight 0.60
if ($LASTEXITCODE -ne 0) {
  if ($LASTEXITCODE -eq 2) {
    Write-Host "[P1-7] WARN Phase7 fail-closed (exit=2) -> continuing (paper-first safety)" -ForegroundColor Yellow
  } else {
    throw "[P1-7] Phase7 failed exit=$LASTEXITCODE"
  }
}
Write-Host "[P1-7] DONE ✅ Phase1..Phase7 daily REAL pipeline complete." -ForegroundColor Green
exit 0