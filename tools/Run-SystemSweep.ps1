[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Say($tag,$msg){ "{0} {1}" -f $tag,$msg | Out-Host }
function Ok($msg){ Say "[OK ]" $msg }
function Warn($msg){ Say "[WARN]" $msg }
function Fail($msg){ Say "[FAIL]" $msg; $script:failCount++ }
function Missing($msg){ Say "[MISS]" $msg; $script:missCount++ }

$script:failCount = 0
$script:missCount = 0

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
if(-not (Test-Path (Join-Path $repoRoot ".git"))){ throw "NOT_IN_REPO_ROOT: $repoRoot" }
$tools = Join-Path $repoRoot "tools"
$logs  = Join-Path $repoRoot "logs"
$src   = Join-Path $repoRoot "src"
$cfg   = Join-Path $repoRoot "config"

Say "[INFO]" ("RepoRoot=" + $repoRoot)

# -------------------------
# 0) Hygiene / integrity
# -------------------------
$corrupt = @(Get-ChildItem -LiteralPath $tools -File -Filter "*.corrupt_saved_*" -ErrorAction SilentlyContinue)
if($corrupt.Count -gt 0){
  Warn ("CorruptSavedFiles=" + $corrupt.Count)
  $corrupt | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize | Out-Host
}else{ Ok "No *.corrupt_saved_* in tools/" }

# UTF-8 BOM scan (fast heuristic)
$ps1 = @(Get-ChildItem -LiteralPath $tools -File -Filter "*.ps1" -ErrorAction SilentlyContinue)
$withBom = @()
foreach($p in $ps1){
  $b = [System.IO.File]::ReadAllBytes($p.FullName)
  if($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF){ $withBom += $p }
}
if($withBom.Count -gt 0){
  Fail ("UTF8_BOM_FOUND in tools/: " + ($withBom | Select-Object -ExpandProperty Name -First 10 -ErrorAction SilentlyContinue) -join ", ")
}else{ Ok "tools/*.ps1 appear UTF-8 no BOM" }

# StrictMode parse check (all tools)
$parseErr = 0
foreach($p in $ps1){
  $errs=$null
  [void][System.Management.Automation.Language.Parser]::ParseFile($p.FullName,[ref]$null,[ref]$errs)
  if(@($errs).Count -gt 0){
    $parseErr += 1
    Warn ("ParseErrors in " + $p.Name + " count=" + @($errs).Count)
  }
}
if($parseErr -gt 0){ Fail ("tools parse errors in " + $parseErr + " file(s)") } else { Ok "All tools/*.ps1 parse clean" }

# -------------------------
# 1) Phase 1: replay bars present?
# -------------------------
# Heuristic: presence of replay outputs/logs and bar completeness tools
$mustTools = @(
  "Test-BarCompleteness.ps1",
  "Test-SessionBoundaries.ps1",
  "Normalize-SessionTags.ps1"
)
foreach($t in $mustTools){
  $p = Join-Path $tools $t
  if(Test-Path -LiteralPath $p){ Ok ("Phase1 tool present: " + $t) } else { Missing ("Phase1 tool missing: " + $t) }
}

# -------------------------
# 2) Phase 2/3: GateScore events + daily build
# -------------------------
$gsBuild = Join-Path $tools "Run-GateScoreDailyBuild.ps1"
if(Test-Path -LiteralPath $gsBuild){ Ok "GateScore daily build tool present" } else { Missing "Run-GateScoreDailyBuild.ps1 missing" }

# Events files existence
$syms = if($Symbol -eq "ALL") { @("NVDA","SPY","QQQ") } else { @($Symbol) }
foreach($s in $syms){
  $main = Join-Path $logs ("{0}_gatescore_events.jsonl" -f $s.ToLower())
  $real = Join-Path $logs ("{0}_gatescore_events_real.jsonl" -f $s.ToLower())
  if(Test-Path $real){ Ok ("Events REAL exists: " + (Split-Path -Leaf $real)) } else { Warn ("Events REAL missing: " + (Split-Path -Leaf $real)) }
  if(Test-Path $main){ Ok ("Events MAIN exists: " + (Split-Path -Leaf $main)) } else { Missing ("Events MAIN missing: " + (Split-Path -Leaf $main)) }
}

# -------------------------
# 3) Phase 4: validation freshness
# -------------------------
$p4 = Join-Path $logs "phase4_validation_passed.json"
if(Test-Path $p4){
  try{
    $j = (Get-Content -LiteralPath $p4 -Raw -Encoding utf8) | ConvertFrom-Json
    $asOf = ([string]$j.as_of_date).Substring(0,10)
    $ok = [bool]$j.phase4_ok_today
    Ok ("Phase4 file ok: as_of=" + $asOf + " ok=" + $ok)
  } catch { Fail "Phase4 file exists but cannot parse" }
}else{ Missing "phase4_validation_passed.json missing" }

# -------------------------
# 4) Phase 5: Block-G contract builder + checker
# -------------------------
$builder = Join-Path $tools "Build-BlockGStatusStub.ps1"
$checker = Join-Path $tools "Check-BlockGReady.ps1"
$preflight = Join-Path $tools "Run-Phase5PreflightGate.ps1"

foreach($p in @($builder,$checker,$preflight)){
  if(Test-Path $p){ Ok ("Phase5 tool present: " + (Split-Path -Leaf $p)) } else { Missing ("Phase5 tool missing: " + (Split-Path -Leaf $p)) }
}

# Build contract now (fail-closed)
if(Test-Path $builder){
  try{
    & $builder | Out-Host
    Ok "BlockG builder executed"
  } catch {
    Fail ("BlockG builder failed: " + $_.Exception.Message)
  }
}else{
  Warn "Skip builder run (missing)"
}

$stub = Join-Path $logs "blockg_status_stub.json"
if(Test-Path $stub){
  try{
    $st = (Get-Content -LiteralPath $stub -Raw -Encoding utf8) | ConvertFrom-Json
    Ok ("BlockG stub present: as_of=" + $st.as_of_date + " nvda_ready=" + $st.nvda_blockg_ready)
    # Contract required fields (institutional)
    $req = @(
      "phase23_health_ok_today",
      "phase4_ok_today",
      "ev_hard_daily_ok_today",
      "gatescore_fresh_today",
      "gatescore_ok_today",
      "nvda_blockg_ready"
    )
    foreach($k in $req){
      if($st.PSObject.Properties.Name -contains $k){ Ok ("Contract field: " + $k + "=" + $st.$k) } else { Missing ("Contract missing field: " + $k) }
    }
  } catch {
    Fail "BlockG stub exists but cannot parse"
  }
}else{ Missing "logs/blockg_status_stub.json missing" }

# Checker semantics: should be contract-only (no recompute)
if(Test-Path $checker){
  $txt = Get-Content -LiteralPath $checker -Raw -Encoding utf8
  if($txt -match 'blockg_status_stub\.json'){ Ok "Check-BlockGReady uses contract json" } else { Warn "Check-BlockGReady may not use contract json (verify)" }
}else{ Warn "Skip checker scan (missing)" }

# -------------------------
# 5) Phase 6: Intel pipeline smoke
# -------------------------
$intel = Join-Path $tools "Run-IntelPipeline.ps1"
if(Test-Path $intel){
  Ok "Intel tool present"
  # smoke-run in try (should not throw)
  try{
    & $intel -ErrorAction Stop | Out-Host
    Ok "Intel pipeline executed (smoke)"
  } catch {
    Fail ("Intel pipeline failed: " + $_.Exception.Message)
  }
}else{ Missing "Run-IntelPipeline.ps1 missing" }

# -------------------------
# 6) Phase 7: Portfolio metrics/exporters (presence check)
# -------------------------
$maybe = @(
  "Build-Phase6PortfolioMetrics.ps1",
  "Export-Phase5EvBandDailySummary.ps1",
  "Build-GateScorePnlSummary.ps1",
  "Build-GateScorePnlSummaryAllDates.ps1"
)
foreach($t in $maybe){
  $p = Join-Path $tools $t
  if(Test-Path $p){ Ok ("Portfolio/metrics tool present: " + $t) } else { Warn ("Portfolio/metrics tool missing: " + $t) }
}

# -------------------------
# 7) Python enforcement hooks (presence check only)
# -------------------------
$pyGuard = Join-Path $src "hybrid_ai_trading\execution\execution_engine_phase5_guard.py"
if(Test-Path $pyGuard){ Ok "Python Phase5 guard exists" } else { Missing "execution_engine_phase5_guard.py missing" }

# Summary
Say "[INFO]" ("MISS=" + $script:missCount + " FAIL=" + $script:failCount)
if($script:failCount -gt 0){ exit 2 }
if($script:missCount -gt 0){ exit 1 }
exit 0
