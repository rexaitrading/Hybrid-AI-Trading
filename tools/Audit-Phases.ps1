[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

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

function RunPSNonFatal([string]$label,[string]$rel,[string[]]$args=@()){
  $p = Join-Path $root $rel
  if (-not (Test-Path $p)) { W ("[SKIP] {0} missing: {1}" -f $label,$rel); return }
  W ("[RUN] {0}: {1} {2}" -f $label,$rel,($args -join " "))

  $oldEap = $ErrorActionPreference
  try {
    $ErrorActionPreference="Continue"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $p @args 2>&1 | ForEach-Object { W ("  " + $_) }
    W ("[RC] {0} = {1}" -f $label,$LASTEXITCODE)
  } finally {
    $ErrorActionPreference=$oldEap
  }
}

Section "Repo + environment"
W ("root=" + $root)
W ("ts=" + $ts)

Section "Phase 1 (Replay / Backtest)"
CheckPath "Replay package" "src\hybrid_ai_trading\replay"
CheckPath "Backtest replay CLI" "src\hybrid_ai_trading\runners\backtest_replay.py"
CheckPath "Replay micro runner" "src\hybrid_ai_trading\runners\replay_micro.py"

Section "Phase 2 (Microstructure / Cost Model)"
CheckPath "Phase2 package" "src\hybrid_ai_trading\phase2"
CheckPath "Micro cost snapshot" "src\hybrid_ai_trading\phase2\micro_cost_snapshot.py"
CheckPath "Phase2_3 diagnostics doc" "docs\Phase2_3_Diagnostics.md"

Section "Phase 3/4/5 (Per-Market receipts)"
$canonMkts = @("US","JP","HK","HK_SH","HK_SZ","SG","IN","KR","TW")
foreach($m in $canonMkts){
  $mU = ($m + "").ToUpperInvariant()
  Section ("Market " + $mU)

  # Phase 3
  CheckPath ("GateScore daily summary csv [" + $mU + "]") ("logs\" + $mU + "\gatescore_daily_summary.csv")

  # Phase 4
  CheckPath ("Phase4 stamp [" + $mU + "]") ("logs\" + $mU + "\phase4_validation_passed.json")

  # Phase 5
  CheckPath ("Block-G status [" + $mU + "]") ("logs\" + $mU + "\blockg_status_stub.json")

  # Build contract per market (safe, deterministic). Nonfatal.
  RunPSNonFatal ("BlockG build [" + $mU + "]") "tools\Build-BlockGStatusStub.ps1" @("-Market",$mU,"-Symbol","ALL")
}

Section "Phase 6 (Portfolio / Aggregation)"
CheckPath "Phase6 module" "src\hybrid_ai_trading\phase6"
CheckPath "Phase6 daily summary json" "logs\phase6\phase6_daily_summary.json"

Section "Phase 7 (Optimizer)"
CheckPath "Phase7 module" "src\hybrid_ai_trading\phase7"
CheckPath "Phase7 weights json" "logs\phase7\phase7_weights.json"

Section "DONE"
W ("report=" + $report)
Write-Host "[AUDIT] Wrote $report" -ForegroundColor Green
exit 0
