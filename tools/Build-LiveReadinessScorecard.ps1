[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol="NVDA",

  [string]$OutPath = ".\logs\live_readiness_scorecard.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function ToI([object]$v){ $x=0; [void][int]::TryParse([string]$v,[ref]$x); return $x }
function ToD([object]$v){ $x=0.0; [void][double]::TryParse([string]$v,[ref]$x); return $x }
function NowUtc(){ (Get-Date).ToUniversalTime().ToString("o") }

$repoRoot = (Resolve-Path ".").Path
$logsDir  = Join-Path $repoRoot "logs"
$outFull  = (Resolve-Path ".").Path + "\" + $OutPath.TrimStart(".\")
$enc = New-Object System.Text.UTF8Encoding($false)

# --- Load BlockG status (single source for readiness booleans) ---
$stPath = Join-Path $logsDir "blockg_status_stub.json"
if(-not (Test-Path -LiteralPath $stPath)){ throw "Missing: $stPath" }
$st = Get-Content -LiteralPath $stPath -Raw -Encoding utf8 | ConvertFrom-Json

$sym = $Symbol.ToUpperInvariant()
$gsb = $null
try { $gsb = $st.gatescore_by_symbol.$sym } catch { $gsb = $null }

# --- Phase signals (from contract snapshot) ---
$marketClosed = [bool]$st.market_closed_today
$phase4Ok     = [bool]$st.phase4_ok_today
$phase23Ok    = [bool]$st.phase23_health_ok_today
$evHardOk     = [bool]$st.ev_hard_daily_ok_today

$gsFreshToday = [bool]$st.gatescore_fresh_today
$gsRecent     = [bool]$st.gatescore_recent_enough
$gsOkLive     = [bool]$st.gatescore_ok_live_today
$gsMsSource   = ([string]$st.gatescore_metrics_source).Trim()

# --- Per-symbol readiness flag from contract ---
$keyReady = ($sym.ToLower() + "_blockg_ready")
$symReady = $false
try { $symReady = [bool]$st.$keyReady } catch { $symReady = $false }

# --- Pull today/session numeric metrics (best effort) ---
$cnt = 0; $pnl = 0; $edge = 0.0; $micro = 0.0
try {
  if($gsb){
    $cnt   = ToI $gsb.count_signals
    $pnl   = ToI $gsb.pnl_samples
    $edge  = ToD $gsb.mean_edge_ratio
    $micro = ToD $gsb.mean_micro_score
  }
} catch { }

# --- Hard minima (from contract snapshot) ---
$minSignalsLive = ToI $st.gatescore_min_samples_live
$minPnlLive     = ToI $st.gatescore_min_pnl_samples_live
$minEdgeLive    = ToD $st.gatescore_min_edge_ratio_live
$minMicroLive   = ToD $st.gatescore_min_micro_score_live

# --- GateScore live-gap diagnostics ---
$gapSignals = $minSignalsLive - $cnt
$gapPnl     = $minPnlLive     - $pnl
$gapEdge    = [Math]::Round($minEdgeLive  - $edge, 6)
$gapMicro   = [Math]::Round($minMicroLive - $micro, 6)

# --- Profitability Confidence (strict heuristic) ---
# Start at 0. Add points only on "real + sufficient + open day".
$scorePts = 0
$maxPts   = 100
$reasons  = New-Object System.Collections.Generic.List[string]

# Safety lock (not profitability, but required prerequisite) -> +15 if present
$lockPackPath = Join-Path $repoRoot "tools\Run-BlockGLockPack.ps1"
if(Test-Path $lockPackPath){ $scorePts += 15 } else { $reasons.Add("missing_lockpack_tool") | Out-Null }

# Market-open requirement -> +10 only when market_closed_today=false
if(-not $marketClosed){ $scorePts += 10 } else { $reasons.Add("market_closed_today=true (profitability score capped)") | Out-Null }

# Data source requirement -> +15 if not proxy/stub
if($gsMsSource -and ($gsMsSource -notmatch '^(?i)proxy_') -and ($gsMsSource -notmatch '^(?i)stub')){ $scorePts += 15 } else { $reasons.Add("gatescore_metrics_source_not_live_grade=" + $gsMsSource) | Out-Null }

# Freshness -> +10
if($gsFreshToday -and $gsRecent){ $scorePts += 10 } else { $reasons.Add("gatescore_not_fresh_or_recent") | Out-Null }

# Prereqs -> +15
if($phase4Ok -and $phase23Ok -and $evHardOk){ $scorePts += 15 } else { $reasons.Add("prereq_failed p4=" + $phase4Ok + " p23=" + $phase23Ok + " evHard=" + $evHardOk) | Out-Null }

# Live hard thresholds -> +35
if($gsOkLive -and $cnt -ge $minSignalsLive -and $pnl -ge $minPnlLive -and $edge -ge $minEdgeLive -and $micro -ge $minMicroLive){
  $scorePts += 35
} else {
  $reasons.Add(("live_thresholds_not_met cnt=" + $cnt + " pnl=" + $pnl + " edge=" + $edge + " micro=" + $micro)) | Out-Null
  $reasons.Add(("gaps signals=" + $gapSignals + " pnl=" + $gapPnl + " edge=" + $gapEdge + " micro=" + $gapMicro)) | Out-Null
}

# Convert to 0..1 confidence
$confidence = [Math]::Round(([double]$scorePts / [double]$maxPts), 4)

$out = [ordered]@{
  ts_utc = (NowUtc)
  symbol = $sym
  branch = (git rev-parse --abbrev-ref HEAD).Trim()
  head   = (git rev-parse --short HEAD).Trim()

  safety_lockpack_required = $true
  market_closed_today = $marketClosed

  prereqs = [ordered]@{
    phase4_ok_today = $phase4Ok
    phase23_health_ok_today = $phase23Ok
    ev_hard_daily_ok_today = $evHardOk
  }

  gatescore = [ordered]@{
    metrics_source = $gsMsSource
    fresh_today = $gsFreshToday
    recent_enough = $gsRecent
    ok_live_today = $gsOkLive
    by_symbol = [ordered]@{
      count_signals = $cnt
      pnl_samples = $pnl
      mean_edge_ratio = $edge
      mean_micro_score = $micro
    }
    live_minima = [ordered]@{
      min_signals = $minSignalsLive
      min_pnl_samples = $minPnlLive
      min_edge_ratio = $minEdgeLive
      min_micro_score = $minMicroLive
    }
    live_gaps = [ordered]@{
      signals_gap = $gapSignals
      pnl_samples_gap = $gapPnl
      edge_gap = $gapEdge
      micro_gap = $gapMicro
    }
  }

  contract_ready_flag = [ordered]@{
    key = $keyReady
    value = $symReady
  }

  profitability_confidence = [ordered]@{
    points = $scorePts
    max_points = $maxPts
    confidence_0_to_1 = $confidence
    confidence_0_to_10 = [Math]::Round($confidence * 10.0, 2)
    notes = @($reasons)
  }
} | ConvertTo-Json -Depth 8

$out = $out -replace "`r`n","`n"
if($out.Length -gt 0 -and $out[-1] -ne "`n"){ $out += "`n" }
[System.IO.File]::WriteAllText($outFull, $out, $enc)

Write-Host ("[SCORECARD] wrote " + $outFull) -ForegroundColor Green
exit 0
