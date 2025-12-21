[CmdletBinding()]
param(
  [int]$TimeoutSec = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "[AUDIT] Python missing: $py" }

$env:PYTHONNOUSERSITE="1"
$env:PYTHONPATH = (Join-Path $root "src")
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"

$ts = (Get-Date).ToString("yyyyMMdd_HHmmss")
$outDir = Join-Path $root "logs\audit"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$report = Join-Path $outDir ("phase_audit_" + $ts + ".txt")

function W([string]$s){ Add-Content -LiteralPath $report -Encoding utf8 -Value $s }
function Section([string]$name){
  W ""
  W ("="*90)
  W $name
  W ("="*90)
}

function CheckPath([string]$label,[string]$rel){
  $p = Join-Path $root $rel
  $ok = Test-Path $p
  W ("[{0}] {1} -> {2}" -f ($(if($ok){"OK"}else{"MISSING"}), $label, $rel))
}

function RunPS([string]$label,[string]$rel,[string[]]$args=@()){
  $p = Join-Path $root $rel
  if (-not (Test-Path $p)) { W ("[SKIP] {0} missing: {1}" -f $label,$rel); return }
  W ("[RUN] {0}: {1} {2}" -f $label,$rel,($args -join " "))
  & powershell -NoProfile -ExecutionPolicy Bypass -File $p @args 2>&1 | ForEach-Object { W ("  " + $_) }
  W ("[RC] {0} = {1}" -f $label,$LASTEXITCODE)
}

function RunPyTimeout([string]$label,[string[]]$args,[int]$timeoutSec){
  Section $label

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $py
  $psi.Arguments = ($args -join " ")
  $psi.WorkingDirectory = $root
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError  = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  [void]$p.Start()

  if (-not $p.WaitForExit($timeoutSec * 1000)) {
    try { $p.Kill($true) } catch { }
    W ("[TIMEOUT] " + $label + " after " + $timeoutSec + "s")
    W ("[RC] " + $label + " = 124")
    return
  }

  $stdout = $p.StandardOutput.ReadToEnd()
  $stderr = $p.StandardError.ReadToEnd()
  if ($stdout) { $stdout -split "`r?`n" | ForEach-Object { if($_){ W ("  " + $_) } } }
  if ($stderr) { $stderr -split "`r?`n" | ForEach-Object { if($_){ W ("  " + $_) } } }

  W ("[RC] " + $label + " = " + $p.ExitCode)
}

Section "Repo + environment"
W ("root=" + $root)
W ("python=" + $py)
& $py -c "import sys; print(sys.version)" 2>&1 | ForEach-Object { W ("  " + $_) }

Section "Phase 1 (Replay / Backtest)"
CheckPath "Replay runner(s)" "src\hybrid_ai_trading\replay"
CheckPath "Backtest replay CLI" "src\hybrid_ai_trading\runners\backtest_replay.py"
CheckPath "Replay micro runner" "src\hybrid_ai_trading\runners\replay_micro.py"

Section "Phase 2 (Microstructure / Cost Model)"
CheckPath "Phase2 package" "src\hybrid_ai_trading\phase2"
CheckPath "Micro cost snapshot" "src\hybrid_ai_trading\phase2\micro_cost_snapshot.py"
CheckPath "Phase2 docs" "docs\Phase2_3_Diagnostics.md"

Section "Phase 3 (GateScore)"
CheckPath "GateScore daily summary csv" "logs\gatescore_daily_summary.csv"
CheckPath "GateScore thresholds" "configs\blockg_thresholds.json"
CheckPath "GateScore package" "src\hybrid_ai_trading\gatescore"

Section "Phase 4 (Validation)"
CheckPath "Phase4 stamp" "logs\phase4_validation_passed.json"
CheckPath "Phase4 module" "src\hybrid_ai_trading\phase4"

Section "Phase 5 (Risk + Execution perimeter)"
CheckPath "Block-G status" "logs\blockg_status_stub.json"
CheckPath "Block-G builder" "tools\Build-BlockGStatusStub.ps1"
CheckPath "Block-G checker" "tools\Check-BlockGReady.ps1"
CheckPath "Smoke live fail-closed" "tools\Smoke-LiveIbFailClosed.ps1"
CheckPath "IB adapter" "src\hybrid_ai_trading\brokers\ib_adapter.py"
CheckPath "Execution engine" "src\hybrid_ai_trading\execution\execution_engine.py"
RunPS "BlockG build" "tools\Build-BlockGStatusStub.ps1"
RunPS "BlockG check NVDA" "tools\Check-BlockGReady.ps1" @("-Symbol","NVDA")
RunPS "Smoke live fail-closed" "tools\Smoke-LiveIbFailClosed.ps1" @("-Symbol","NVDA")

Section "Phase 6 (Portfolio / Multi-strategy aggregator)"
CheckPath "Phase6 daily summary json" "logs\phase6\phase6_daily_summary.json"
CheckPath "Phase6 module" "src\hybrid_ai_trading\phase6"

Section "Phase 7 (Optimizer)"
CheckPath "Phase7 weights json" "logs\phase7\phase7_weights.json"
CheckPath "Phase7 module" "src\hybrid_ai_trading\phase7"

RunPyTimeout "Python compile sweep (src/)" @("-c","import compileall,sys; ok=compileall.compile_dir('src',quiet=1); print('compileall_ok',ok); sys.exit(0 if ok else 1)") $TimeoutSec
RunPyTimeout "Pytest collect-only" @("-m","pytest","-q","--collect-only") $TimeoutSec

Section "DONE"
W ("report=" + $report)
Write-Host "[AUDIT] Wrote $report" -ForegroundColor Green
exit 0
