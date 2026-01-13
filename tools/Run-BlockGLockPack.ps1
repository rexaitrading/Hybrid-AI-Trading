[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ","CN_SH","CN_SZ")] [string]$Market="US",
  [ValidateSet("NVDA","SPY","QQQ")] [string]$Symbol="NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir


Write-Host "`n[BLOCKG-LOCKPACK] 1) closed-day semantics (ready=10 diag=0)..." -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-BlockGWeekendSemantics.ps1 -Market $Market -Symbol $Symbol | Out-Host
if($LASTEXITCODE -ne 0){ throw "[BLOCKG-LOCKPACK] Weekend semantics failed" }

Write-Host "`n[BLOCKG-LOCKPACK] 2) no-bypass (READY execution allowlist)..." -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-BlockGNoBypass.ps1 | Out-Host
if($LASTEXITCODE -ne 0){ throw "[BLOCKG-LOCKPACK] No-bypass failed" }

Write-Host "`n[BLOCKG-LOCKPACK] 3) READY executor list (must be Arm-NVDA-Live only)..." -ForegroundColor Cyan
# --- A4 Step3 (v2): READY executor list is defined as Invoke-BlockGCheck.ps1 in ALL_STRICT mode ---
# 0) Direct Check-BlockGReady executions must be ZERO.
$patDirect = 'powershell\s+-NoProfile.*-File\s+.*Check-BlockGReady\.ps1|powershell\s+-NoProfile.*Check-BlockGReady\.ps1|&\s*"\.\\tools\\Check-BlockGReady\.ps1"|&\s*\.\\tools\\Check-BlockGReady\.ps1'
$hitsDirect = @(Select-String -Path .\tools\*.ps1 -Pattern $patDirect -ErrorAction SilentlyContinue)

# A4 policy: Arm-NVDA-Live.ps1 is the only approved direct caller of Check-BlockGReady.ps1
$hitsDirect = @($hitsDirect | Where-Object { -not ($_.Line -match '^\s*#') })
$hitsDirect = @($hitsDirect | Where-Object { ([string]$_.Path) -notmatch '\\tools\\Run-BlockGLockPack\.ps1$' })
$hitsDirect = @($hitsDirect | Where-Object { ([string]$_.Path) -notmatch '\\tools\\Arm-NVDA-Live\.ps1$' })

if($hitsDirect -and $hitsDirect.Count -gt 0){
  $p2 = @($hitsDirect | ForEach-Object { [string]$_.Path } | Sort-Object -Unique)
  throw ("[BLOCKG-LOCKPACK] FAIL: direct Check-BlockGReady execution detected:`n" + ($p2 -join "`n"))
}

# 1) READY executor definition (UPDATED):
#    READY executor is Arm-NVDA-Live.ps1, and it must EXECUTE Check-BlockGReady.ps1 directly (deterministic gating).
$armPath = (Resolve-Path -LiteralPath .\tools\Arm-NVDA-Live.ps1).Path
$patArmExec = 'powershell\s+-NoProfile.*-File\s+.*Check-BlockGReady\.ps1|powershell\s+-NoProfile.*Check-BlockGReady\.ps1|&\s*"\.\\tools\\Check-BlockGReady\.ps1"|&\s*\.\\tools\\Check-BlockGReady\.ps1'
$armHits = @(Select-String -LiteralPath $armPath -Pattern $patArmExec -ErrorAction SilentlyContinue)
$armHits = @($armHits | Where-Object { -not ($_.Line -match '^\s*#') })
if($armHits.Count -lt 1){
  throw "[BLOCKG-LOCKPACK] READY executor missing: Arm-NVDA-Live.ps1 does not EXECUTE Check-BlockGReady.ps1"
}
Write-Host ("[BLOCKG-LOCKPACK] READY executor OK: " + $armPath) -ForegroundColor Green

# Fail-closed: ensure repo src/ is on sys.path for this probe.
$env:PYTHONPATH = (Join-Path $repoRoot "src")
python -c "import hybrid_ai_trading.brokers.ib_adapter as a; import hybrid_ai_trading.execution.execution_engine_phase5_guard as g; print('PY_IMPORT_OK')" | Out-Host
if($LASTEXITCODE -ne 0){
  Write-Host ("PY_IMPORT_FAIL (exit=" + $LASTEXITCODE + ")") -ForegroundColor Red
  exit 2
}

Write-Host "`n[BLOCKG-LOCKPACK] PASS" -ForegroundColor Green
exit 0
