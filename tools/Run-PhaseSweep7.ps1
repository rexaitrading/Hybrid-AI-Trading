[CmdletBinding()]
param()


# --- repo root bootstrap (env-first) ---
$repoRoot = ($env:HAT_REPO_ROOT + "").Trim()
if(-not $repoRoot){
  $repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
}
if(-not $repoRoot){ throw "[REPOROOT] FAIL-CLOSED: repoRoot empty (env+Go-RepoRoot)" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# PS5.1-safe UTF-8 IO
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8

$today = (Get-Date).ToString("yyyy-MM-dd")
$repo  = (Get-Location).Path

function Ok([string]$msg){ Write-Host "[OK]  $msg" -ForegroundColor Green }
function Warn([string]$msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Fail([string]$msg){ Write-Host "[FAIL] $msg" -ForegroundColor Red }

Write-Host ("==================== 7-PHASE SWEEP ($today) ====================")

# -------- Phase 0: Hygiene / BOM --------
Write-Host "--- Phase0: Hygiene ---"
$badBom = @()
Get-ChildItem .\tools, .\src -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Extension -in ".ps1",".py",".md",".json",".yaml",".yml" } |
  ForEach-Object {
    try {
      $b = [System.IO.File]::ReadAllBytes($_.FullName)
      if($b.Length -ge 3 -and $b[0]-eq 0xEF -and $b[1]-eq 0xBB -and $b[2]-eq 0xBF){ $badBom += $_.FullName }
    } catch {}
  }
if($badBom.Count -gt 0){
  Fail ("UTF8 BOM found (sample): " + (($badBom | Select-Object -First 5) -join "; "))
} else {
  Ok "No UTF8 BOM detected in tools/src (sampled)"
}

# -------- Phase 1: Replay presence --------
Write-Host "--- Phase1: Replay ---"
if(Test-Path .\runners\backtest_replay.py){ Ok "Phase1 replay runner exists" } else { Warn "Missing runners\backtest_replay.py (if renamed, update docs)" }

# -------- Phase 2/3: Phase23 health + GateScore artifacts --------
Write-Host "--- Phase2/3: Health + GateScore ---"

# Phase23 schema: date + phase23_ok (your repo)
if (Test-Path .\logs\phase23_health_daily.csv) {
  $last = (Import-Csv .\logs\phase23_health_daily.csv | Select-Object -Last 1)

  $dateKey = @("as_of_date","date","today","session","day","ts","ts_utc") |
    Where-Object { $last.PSObject.Properties.Name -contains $_ } |
    Select-Object -First 1

  $okKey = @("phase23_ok","ok","ok_today","passed","pass","is_ok","health_ok") |
    Where-Object { $last.PSObject.Properties.Name -contains $_ } |
    Select-Object -First 1

  if (-not $dateKey -or -not $okKey) {
    Fail ("phase23_health_daily schema unexpected. headers=" + (($last.PSObject.Properties.Name) -join ","))
  } else {
    $d = ($last.$dateKey + "")
    if ($d.Length -ge 10) { $d = $d.Substring(0,10) }
    $okv = ($last.$okKey + "").ToLowerInvariant()
    $okb = ($okv -in @("true","1","yes","y"))

    if ($d -eq $today -and $okb) { Ok "phase23_health_daily OK today" }
    else { Fail ("phase23_health_daily stale/not ok: date=$d ok=$okv") }
  }
} else {
  Fail "Missing logs\phase23_health_daily.csv"
}

if(Test-Path .\logs\gatescore_pnl_summary.csv){
  $rows = @(Import-Csv .\logs\gatescore_pnl_summary.csv | Where-Object { $_.as_of_date -eq $today })
  if($rows.Count -gt 0){ Ok ("GateScore pnl_summary today rows: " + (($rows | Select-Object -ExpandProperty symbol) -join ",")) }
  else { Fail "GateScore pnl_summary missing today rows" }
} else { Fail "Missing logs\gatescore_pnl_summary.csv" }

# -------- Phase 4: Required guard slice --------
Write-Host "--- Phase4: Validation ---"
pytest -q tests/test_execution_engine_phase5_guard.py tests/test_ib_phase5_guard.py | Out-Host
if($LASTEXITCODE -eq 0){ Ok "Phase4 required guard slice green" } else { Fail "Phase4 guard slice failed" }

# -------- Phase 5: EV-hard + BlockG --------
Write-Host "--- Phase5: EV-hard + BlockG ---"
if(Test-Path .\logs\ev_hard_snapshot.json){
  $ev = Get-Content .\logs\ev_hard_snapshot.json -Raw -Encoding utf8 | ConvertFrom-Json
  if(($ev.as_of_date + "") -eq $today -and ($ev.ok -eq $true)){ Ok "EV-hard snapshot OK today" } else { Fail "EV-hard snapshot stale/not ok" }
} else { Fail "Missing logs\ev_hard_snapshot.json" }

if(Test-Path .\logs\blockg_status_stub.json){
  $bg = Get-Content .\logs\blockg_status_stub.json -Raw -Encoding utf8 | ConvertFrom-Json
  if(($bg.as_of_date + "") -eq $today -and ($bg.nvda_blockg_ready -eq $true)){ Ok "BlockG NVDA READY today" } else { Fail "BlockG not ready/stale" }
} else { Fail "Missing logs\blockg_status_stub.json" }

# -------- Phase 6: Core ops tools presence --------
Write-Host "--- Phase6: Core ops tools ---"
$need = @(
  ".\tools\Run-DailyProducersSuite.ps1",
  ".\tools\Run-PreMarketBlockG.ps1",
  ".\tools\Invoke-BlockGCheck.ps1",
  ".\tools\Check-BlockGReady.ps1"
)
$missing = @($need | Where-Object { -not (Test-Path $_) })
if($missing.Count -eq 0){ Ok "Core ops tools present" } else { Fail ("Missing tools: " + ($missing -join ", ")) }

# -------- Phase 7: Optimizer presence --------
Write-Host "--- Phase7: Optimizer ---"
if ((Test-Path .\tools\Run-Phase7OptimizerDaily.ps1) -or (Test-Path .\src\hybrid_ai_trading\phase7\optimizer.py)) {
  Ok "Phase7 optimizer entrypoints present"
} else {
  Warn "Phase7 optimizer entrypoints not found (if moved, update tools)"
}

# -------- Runtime: Intel pipeline --------
Write-Host "--- Runtime: Intel ---"
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-IntelPipeline.ps1 | Out-Host
if($LASTEXITCODE -eq 0){ Ok "Intel pipeline runnable (RC=0)" } else { Fail ("Intel pipeline RC=" + $LASTEXITCODE) }

Write-Host "==================== SWEEP COMPLETE ===================="
exit 0