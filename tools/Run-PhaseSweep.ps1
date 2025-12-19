[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [string]$OutDir = "logs\phase_sweep"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
function WriteUtf8NoBom {
  param([Parameter(Mandatory=$true)][string]$Path,[Parameter(Mandatory=$true)][string]$Text)
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Text -replace "`r`n","`n"), $utf8NoBom)
}


function NowStamp { (Get-Date).ToString("yyyyMMdd_HHmmss") }
function TodayStr { (Get-Date).ToString("yyyy-MM-dd") }
function ReadUtf8Raw([string]$path){
  if(-not (Test-Path $path)){ return $null }
  return Get-Content $path -Raw -Encoding utf8
}
function TailUtf8([string]$path, [int]$n){
  if(-not (Test-Path $path)){ return @() }
  return Get-Content $path -Tail $n -Encoding utf8
}
function CsvHasTodayRow([string]$path, [string]$today){
  if(-not (Test-Path $path)){ return $false }
  $lines = Get-Content $path -Encoding utf8
  if($lines.Count -lt 2){ return $false }
  foreach($ln in $lines[1..($lines.Count-1)]){
    if($ln -like "$today,*"){ return $true }
  }
  return $false
}
function Exists($p){ Test-Path $p }
function LastWrite($p){
  if(Test-Path $p){ (Get-Item $p).LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss") } else { "" }
}

function Resolve-RepoRoot {
  # PS5/StrictMode safe: prefer $PSCommandPath (string), fallback to $MyInvocation
  $scriptPath = $PSCommandPath
  if([string]::IsNullOrWhiteSpace($scriptPath)){
    $scriptPath = $MyInvocation.MyCommand.Path
  }
  if([string]::IsNullOrWhiteSpace($scriptPath)){
    throw "PhaseSweep: cannot resolve script path (PSCommandPath/MyInvocation empty)"
  }

  $here = Split-Path -Parent $scriptPath
  $d = (Resolve-Path -LiteralPath $here).ProviderPath

  while($true){
    if(Test-Path -LiteralPath (Join-Path $d ".git")){ return $d }
    $parent = Split-Path -Parent $d
    if([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $d){ break }
    $d = $parent
  }

  throw "PhaseSweep: Could not find .git by walking up from script dir: $here"
}

$repoRoot = Resolve-RepoRoot
Set-Location $repoRoot

$ts = NowStamp
$outRoot = Join-Path $repoRoot $OutDir
New-Item -ItemType Directory -Force -Path $outRoot | Out-Null

$mdPath  = Join-Path $outRoot ("PHASE_SWEEP_{0}.md" -f $ts)
$jsonPath= Join-Path $outRoot ("PHASE_SWEEP_{0}.json" -f $ts)

$branch = (git status -sb | Select-Object -First 1).Trim()
$head5 = (git log -5 --oneline)

# --- Phase signals (file-based + tests keywords) ---
$signals = [ordered]@{
  phase1 = [ordered]@{
    name="Phase-1 Bar Replay"
    src_hits=@(
      "src\hybrid_ai_trading\replay\nvda_bplus_gate_score.py",
      "tests\test_phase1_replay_smoke.py"
    )
    expected_logs=@(
      "logs\gatescore_daily_summary.csv"
    )
    test_k='phase1|replay'
  }
  phase2 = [ordered]@{
    name="Phase-2 Microstructure & Cost Model"
    src_hits=@(
      "src\hybrid_ai_trading\costs\cost_model.py",
      "src\hybrid_ai_trading\kelly_sizer.py"
    )
    expected_logs=@()
    test_k='phase2|micro|cost'
  }
  phase3 = [ordered]@{
    name="Phase-3 GateScore Engine"
    src_hits=@(
      "src\hybrid_ai_trading\gatescore",
      "tools\Run-GateScoreSmoke.ps1",
      "tests\test_phase3_gatescore_quality.py"
    )
    expected_logs=@(
      "logs\gatescore_daily_summary.csv",
      "logs\blockg_status_stub.json"
    )
    test_k='phase3|gatescore'
  }
  phase4 = [ordered]@{
    name="Phase-4 Validation"
    src_hits=@(
      "tools\Run-Phase4Smoke.ps1",
      "logs\phase4_validation_passed.json",
      "tests\test_execution_engine_phase5_guard.py"
    )
    expected_logs=@(
      "logs\phase4_validation_passed.json"
    )
    test_k='phase4|validation'
  }
  phase5 = [ordered]@{
    name="Phase-5 Risk + Block-G Contract + Guard"
    src_hits=@(
      "src\hybrid_ai_trading\execution\execution_engine_phase5_guard.py",
      "src\hybrid_ai_trading\execution\blockg_contract_reader.py",
      "tools\Check-BlockGReady.ps1",
      "tests\test_blockg_checker_contract_only.py"
    )
    expected_logs=@(
      "logs\blockg_status_stub.json",
      "logs\phase23_health_daily.csv",
      "logs\phase5_ev_hard_veto_daily.csv"
    )
    test_k='phase5|blockg|runcontext'
  }
  phase6 = [ordered]@{
    name="Phase-6 Multi-Strategy Router"
    src_hits=@(
      "src\hybrid_ai_trading\portfolio\router.py",
      "tests\test_phase6_router_policy.py"
    )
    expected_logs=@()
    test_k='phase6|router'
  }
  phase7 = [ordered]@{
    name="Phase-7 Portfolio Optimizer"
    src_hits=@(
      "src\hybrid_ai_trading\portfolio_optimizer\optimizer.py",
      "src\hybrid_ai_trading\portfolio_optimizer\constraints.py"
    )
    expected_logs=@(
      "logs\portfolio_optimizer_daily_*.json"
    )
    test_k='phase7|optimizer|portfolio_optimizer'
  }
}

# Helper: resolve wildcard existence for phase7 outputs
function AnyMatch([string]$glob){
  $dir = Split-Path -Parent $glob
  $leaf = Split-Path -Leaf $glob
  if(-not (Test-Path $dir)){ return $false }
  return (Get-ChildItem -Path $dir -Filter $leaf -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0
}

# Test inventory by keyword (quick listing)
$testFiles = Get-ChildItem .\tests -Recurse -File -Include *.py | Select-Object -ExpandProperty FullName

function TestHits([string]$k){
  if([string]::IsNullOrWhiteSpace($k)){ return @() }
  $rx = $k
  $hits = @()
  foreach($f in $testFiles){
    try{
      if(Select-String -Path $f -Pattern $rx -Quiet){
        $hits += $f
      }
    } catch {}
  }
  return ($hits | Sort-Object -Unique)
}

# Evaluate each phase: READY if all src_hits exist + at least 1 test hit; logs are advisory.
$report = [ordered]@{
  ts_local = (Get-Date).ToString("o")
  repo_root = $repoRoot
  branch = $branch
  head5 = $head5
  phases = @()
}

foreach($key in $signals.Keys){
  $s = $signals[$key]
  $srcMissing = @()
  foreach($p in $s.src_hits){
    if(-not (Test-Path (Join-Path $repoRoot $p))){ $srcMissing += $p }
  }

  $logMissing = @()
  foreach($p in $s.expected_logs){
    if($p -like "*`**"){
      if(-not (AnyMatch (Join-Path $repoRoot $p))){ $logMissing += $p }
    } else {
      if(-not (Test-Path (Join-Path $repoRoot $p))){ $logMissing += $p }
    }
  }

  $tHits = TestHits $s.test_k

  $status = "UNKNOWN"
  if($srcMissing.Count -eq 0 -and $tHits.Count -gt 0){ $status = "PRESENT" }
  elseif($srcMissing.Count -gt 0){ $status = "MISSING_FILES" }
  elseif($tHits.Count -eq 0){ $status = "NO_TEST_SIGNAL" }

  $phaseObj = [ordered]@{
    key = $key
    name = $s.name
    status = $status
    missing_src = $srcMissing
    missing_logs = $logMissing
    test_signal_k = $s.test_k
    test_signal_hits = $tHits
  }
  $report.phases += $phaseObj
}

# Roadmap/doc discovery
$docHits = @()
if(Test-Path ".\docs"){
  $docHits = Get-ChildItem .\docs -Recurse -File -Include *.md | Select-Object -ExpandProperty FullName
}

# Basic “roadmap” file presence
$road = [ordered]@{
  docs_dir = (Test-Path ".\docs")
  PATCHLOG = (Test-Path ".\docs\PATCHLOG.md")
  CHANGELOG = (Test-Path ".\docs\CHANGELOG.md")
  ROADMAP = (Test-Path ".\docs\ROADMAP.md")
  CHECKPOINTS = (Test-Path ".\docs\CHECKPOINTS.md")
  OPS_BLOCKG = (Test-Path ".\docs\OPS_BLOCKG.md")
}
$report["docs"] = $road

# Write JSON
WriteUtf8NoBom $jsonPath (($report | ConvertTo-Json -Depth 8))

# Write Markdown
$md = New-Object System.Collections.Generic.List[string]
$null = $md.Add('# Phase Sweep Report')
$null = $md.Add('')
$null = $md.Add('- ts: ' + $report.ts_local)
$null = $md.Add('- branch: ' + $report.branch)
$null = $md.Add('')
$null = $md.Add('## HEAD (last 5)')
foreach($l in $head5){ $null = $md.Add('- ' + $l) }
$null = $md.Add('')
$null = $md.Add('## Docs Presence')
foreach($k in $road.Keys){
  $null = $md.Add(('- {0}: {1}' -f $k, $road[$k]))
}
$null = $md.Add('')
$null = $md.Add('## Phases')
foreach($p in $report.phases){
  $null = $md.Add(('### {0} - {1}' -f $p.key.ToUpper(), $p.name))
  $null = $md.Add(('- status: **{0}**' -f $p.status))
  if($p.missing_src.Count -gt 0){
    $null = $md.Add('- missing src:')
    foreach($m in $p.missing_src){ $null = $md.Add('  - ' + $m) }
  }
  if($p.missing_logs.Count -gt 0){
    $null = $md.Add('- missing logs (advisory):')
    foreach($m in $p.missing_logs){ $null = $md.Add('  - ' + $m) }
  }

  # IMPORTANT: backticks live inside SINGLE-QUOTED string => PS5 safe
  $null = $md.Add(('- test signal regex: `{0}`' -f $p.test_signal_k))
  $null = $md.Add(('- test hits: {0}' -f $p.test_signal_hits.Count))
  $null = $md.Add('')
}

$mdText = ($md.ToArray() -join "`n")
Set-Content -Path $mdPath -Value $mdText -Encoding utf8

Write-Host "[PHASE_SWEEP] Wrote:" -ForegroundColor Green
Write-Host "  $mdPath" -ForegroundColor Green
Write-Host "  $jsonPath" -ForegroundColor Green