[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA",

  [Parameter(Mandatory=$false)]
  [switch]$NoPhase6
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- Resolve repo root safely (supports OneDrive non-ASCII path) ---
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

# --- Ensure UTF-8 output ---
chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

function Fail([string]$Msg){
  Write-Host $Msg -ForegroundColor Red
  throw $Msg
}

Write-Host "=== Phase5->Phase6 PreMarket OneTap ===" -ForegroundColor Cyan
Write-Host "RepoRoot=$repoRoot" -ForegroundColor DarkGray
Write-Host "Symbol=$Symbol" -ForegroundColor DarkGray

# --- (1) Phase-5 Institutional Gate Slice (FAIL-CLOSED) ---
Write-Host "`n[1/4] Gate slice (Phase-5 live boundary)..." -ForegroundColor Yellow
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $py)){ Fail "Missing venv python: $py" }
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Pytest-Chokepoint.ps1 -q `
  tests\execution\test_nvda_live_stamp_gate.py `
  tests\execution\test_ib_safe_chokepoint_blockg.py `
  tests\execution\test_order_manager_blockg_defense_in_depth.py `
  tests\execution\test_blockg_order_manager_guard.py `
  tests\execution\test_blockg_ib_placeorder_guard.py `
  tests\execution\test_blockg_gatescore_policy_session_age.py
if($LASTEXITCODE -ne 0){ Fail "FAIL-CLOSED: Gate slice failed (pytest_exit=$LASTEXITCODE)" }
Write-Host "GATE_SLICE_OK" -ForegroundColor Green

# --- (2) Phase-5 BlockG premarket build + check ---
Write-Host "`n[2/4] BlockG premarket build+check..." -ForegroundColor Yellow
$pre = Join-Path $repoRoot "tools\Run-PreMarketBlockG-Smart.ps1"
if(-not (Test-Path $pre)){ Fail "Missing: $pre" }
$env:HAT_BLOCKG_QUIET = "1"
& $pre -Symbol $Symbol
Remove-Item Env:\HAT_BLOCKG_QUIET -ErrorAction SilentlyContinue
$rc = $LASTEXITCODE
"PREMARKET_BLOCKG_RC=$rc" | Out-Host
$env:HAT_PREMARKET_RC = [string]$rc
if($rc -ne 0){ Fail "FAIL-CLOSED: BlockG premarket script returned $rc" }
Write-Host "BLOCKG_PREMARKET_OK" -ForegroundColor Green

# --- (3) Phase-6 Portfolio state snapshot (optional) ---
if(-not $NoPhase6){
  Write-Host "`n[3/4] Phase-6 portfolio state snapshot..." -ForegroundColor Yellow
  $p6 = Join-Path $repoRoot "tools\Build-Phase6PortfolioState.ps1"
  if(-not (Test-Path $p6)){ Fail "Missing: $p6" }

$env:HAT_BLOCKG_QUIET = "1"
& $p6
Remove-Item Env:\HAT_BLOCKG_QUIET -ErrorAction SilentlyContinue
  $rc6 = $LASTEXITCODE
  "PHASE6_SNAPSHOT_RC=$rc6" | Out-Host
  if($rc6 -ne 0){ Fail "FAIL-CLOSED: Phase6 snapshot failed ($rc6)" }
  Write-Host "PHASE6_SNAPSHOT_OK" -ForegroundColor Green
}else{
  Write-Host "`n[3/4] Phase-6 snapshot skipped (-NoPhase6)" -ForegroundColor DarkYellow
}

# --- (3.5) NVDA live-ready stamp (Phase-5 arming gate) ---
Write-Host "`n[3.5/4] NVDA live-ready stamp..." -ForegroundColor Yellow
$st = Join-Path $repoRoot "tools\Build-NvdaLiveReadyStamp.ps1"
if(-not (Test-Path $st)){ Fail "Missing: $st" }
& $st -BlockGPath (Join-Path $repoRoot "logs\blockg_status_stub.json") -OutPath (Join-Path $repoRoot "logs\nvda_live_ready_stamp.json")
$stRc = $LASTEXITCODE
"NVDA_STAMP_RC=$stRc" | Out-Host
# stamp returning 2 is not a hard failure by itself; readiness summary enforces final decision
# --- \(4\) Readiness summary ---
Write-Host "`n[4/4] Readiness summary..." -ForegroundColor Yellow
$blockg = Join-Path $repoRoot "logs\blockg_status_stub.json"
$stamp  = Join-Path $repoRoot "logs\nvda_live_ready_stamp.json"

$readyBlockg = $false
$readyStamp  = $false

if(Test-Path $blockg){
  try{
    $j = Get-Content $blockg -Raw -Encoding utf8 | ConvertFrom-Json
    # symbol-specific key
    $k = ("{0}_blockg_ready" -f $Symbol.ToLower())
    if($j.PSObject.Properties.Name -contains $k){
      $readyBlockg = [bool]$j.$k
    }
  } catch {}
}

if($Symbol -eq "NVDA"){
  if(Test-Path $stamp){
    try{
      $s = Get-Content $stamp -Raw -Encoding utf8 | ConvertFrom-Json
      if($s.nvda_live_ready -eq $true){ $readyStamp = $true }
    } catch {}
  }
}

Write-Host "READY_BLOCKG=$readyBlockg" -ForegroundColor White
if($Symbol -eq "NVDA"){ Write-Host "READY_STAMP=$readyStamp" -ForegroundColor White }

if(($Symbol -eq "NVDA" -and (-not ($readyBlockg -and $readyStamp))) -or ($Symbol -ne "NVDA" -and (-not $readyBlockg))){
  Fail "NOT_READY: $Symbol (BlockG or Stamp not satisfied)"
}

Write-Host "`nREADY: $Symbol Phase5+Phase6 OK (fail-closed gates passed)" -ForegroundColor Green
exit 0
