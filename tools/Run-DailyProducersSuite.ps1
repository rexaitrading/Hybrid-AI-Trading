[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA"
)
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)


Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-BlockGReady {
  [CmdletBinding()]
  param(
    [ValidateSet("NVDA","SPY","QQQ")]
    [string]$Symbol
  )
  $checker = Join-Path (Split-Path -Parent $PSCommandPath) "Check-BlockGReady.ps1"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "chcp 65001 | Out-Null; [Console]::OutputEncoding=[Text.UTF8Encoding]::new(`$false); `$OutputEncoding=[Text.UTF8Encoding]::new(`$false); & `"$checker`" -Symbol `"$Symbol`"" | Out-Host
  return $LASTEXITCODE
}

$repoRoot = (Resolve-Path ".").Path
Set-Location $repoRoot

$today = (Get-Date).ToString("yyyy-MM-dd")

Write-Host "[DAILY] RepoRoot=$repoRoot" -ForegroundColor Cyan
Write-Host "[DAILY] Symbol=$Symbol" -ForegroundColor Cyan
Write-Host "[DAILY] Today=$today" -ForegroundColor Cyan

# Deterministic Block-G contract path for Python modules
$k = ("HAT_" + "BLOCKG_" + "STATUS_" + "PATH")
[System.Environment]::SetEnvironmentVariable($k, (Join-Path $repoRoot "logs\blockg_status_stub.json"))

# --- 1) EV-HARD snapshot + daily export (fail-closed) ---
$evSnap    = Join-Path $repoRoot "tools\Build-EvHardSnapshot.ps1"
$evCompute = Join-Path $repoRoot "tools\Compute-Phase5EvHardSnapshotInput.ps1"
$evExport  = Join-Path $repoRoot "tools\Export-Phase5EvHardVetoDailySnapshot.ps1"

if (Test-Path $evSnap)    { & $evSnap; if ($LASTEXITCODE -ne 0) { throw "[DAILY] EV-hard snapshot failed" } }
if (Test-Path $evCompute) { & $evCompute -EvidencePath ".\logs\ev_hard_snapshot.json"; if ($LASTEXITCODE -ne 0) { throw "[DAILY] EV-hard compute failed" } }
if (Test-Path $evExport)  { & $evExport; if ($LASTEXITCODE -ne 0) { throw "[DAILY] EV-hard export failed" } }

# --- 2) Phase-4 validation (writes logs/phase4_validation_passed.json) ---
$phase4 = Join-Path $repoRoot "tools\Run-Phase4Validation.ps1"
if (-not (Test-Path $phase4)) { throw "[DAILY] Missing tools\Run-Phase4Validation.ps1" }
& $phase4
if ($LASTEXITCODE -ne 0) { throw "[DAILY] Phase4 validation failed exit=$LASTEXITCODE" }

# Verify Phase4 stamp today + ok=true
$p4 = Join-Path $repoRoot "logs\phase4_validation_passed.json"
if (-not (Test-Path $p4)) { throw "[DAILY] Missing Phase4 stamp: $p4" }
$j4 = Get-Content $p4 -Raw -Encoding utf8 | ConvertFrom-Json
if (($j4.as_of_date + "").Substring(0,10) -ne $today) { throw "[DAILY] Phase4 stale: $($j4.as_of_date) need=$today" }
if (-not [bool]$j4.phase4_ok_today) { throw "[DAILY] Phase4 not ok: $($j4.reason)" }

# --- 3) Phase-3 GateScore daily_build ---
$phase3 = Join-Path $repoRoot "tools\Run-Phase3GateScoreDaily.ps1"
if (-not (Test-Path $phase3)) { throw "[DAILY] Missing tools\Run-Phase3GateScoreDaily.ps1" }
& $phase3 -Symbol $Symbol
$gs = $LASTEXITCODE
if ($gs -ne 0 -and $gs -ne 2) { throw "[DAILY] Phase3 daily_build failed exit=$gs" }

# --- 4) Build Block-G status (single source of truth) ---
$bg = Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1"
if (-not (Test-Path $bg)) { throw "[DAILY] Missing tools\Build-BlockGStatusStub.ps1" }
& $bg | Out-Host
if ($LASTEXITCODE -ne 0) { throw "[DAILY] Build-BlockGStatusStub failed exit=$LASTEXITCODE" }

# Verify Block-G today-ness (contract exists and is for today)
$bst = Join-Path $repoRoot "logs\blockg_status_stub.json"
if (-not (Test-Path $bst)) { throw "[DAILY] Missing BlockG status: $bst" }
$st = Get-Content $bst -Raw -Encoding utf8 | ConvertFrom-Json
if (($st.as_of_date + "").Substring(0,10) -ne $today) { throw "[DAILY] BlockG stale: $($st.as_of_date) need=$today" }

# --- 5) Final fail-closed gate: ONLY via Check-BlockGReady (single semantics owner) ---
$ready = ((Invoke-BlockGReady -Symbol $Symbol) -eq 0)
if (-not $ready) {
  Write-Host ("[DAILY] FAIL-CLOSED: Block-G not ready for {0}" -f $Symbol) -ForegroundColor Yellow
  exit 2
}

Write-Host "[DAILY] DONE [OK] Producers suite complete." -ForegroundColor Green
Write-Host ("[DAILY] Contract snapshot: nvda={0} spy={1} qqq={2}" -f $st.nvda_blockg_ready, $st.spy_blockg_ready, $st.qqq_blockg_ready) | Out-Host
exit 0