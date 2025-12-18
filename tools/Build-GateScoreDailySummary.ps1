[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [ValidateSet("DEV_REPLAY","REAL")]
  [string]$Mode = "DEV_REPLAY"
)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest


function Get-GateScoreSourceFromMode([string]$ModeValue) {
  $m = ("$ModeValue").Trim().ToUpperInvariant()
  if ($m -eq "REAL") { return "REAL" }
  return "DEV_REPLAY"
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$today = (Get-Date).ToString("yyyy-MM-dd")
function Has-TodayLine([string]$p, [string]$today) {
  if (-not (Test-Path $p)) { return $false }
  try {
    $txt = Get-Content $p -Raw -Encoding utf8
    return ($txt -match [regex]::Escape($today))
  } catch { return $false }
}

function Try-BuildRealFromNvdaPaperlive([string]$repoRoot, [string]$logs, [string]$today, [string]$out) {
  $src = Join-Path $logs "nvda_phase5_paperlive_results.jsonl"
  if (-not (Test-Path $src)) { return $false }

  # Compute a conservative REAL proxy:
  # - count_signals = number of rows today with a signal/side field
  # - pnl_samples  = number of rows today with realized_pnl field (even if 0.0)
  # - mean_edge_ratio = average edge_ratio if present else 0
  # - mean_micro_score = average micro_score if present else 0
  $lines = @(Get-Content $src -Encoding utf8)
  if (-not $lines) { return $false }

  $nSignals = 0
  $nPnL = 0
  $sumEdge = 0.0
  $sumMicro = 0.0
  $nEdge = 0
  $nMicro = 0

  foreach ($ln in $lines) {
    if ([string]::IsNullOrWhiteSpace($ln)) { continue }
    try { $o = $ln | ConvertFrom-Json -ErrorAction Stop } catch { continue }

    $ts = ""
    foreach ($k in @("ts_trade","entry_ts")) {
      $p = $o.PSObject.Properties[$k]
      if ($null -ne $p -and $null -ne $p.Value) { $ts = "$($p.Value)"; break }
    }
    if ([string]::IsNullOrWhiteSpace($ts)) {
      # nested fallback: extra.entry_ts
      $p2 = $o.PSObject.Properties["extra"]
      if ($null -ne $p2 -and $null -ne $p2.Value) {
        try {
          $ex = $p2.Value
          $p3 = $ex.PSObject.Properties["entry_ts"]
          if ($null -ne $p3 -and $null -ne $p3.Value) { $ts = "$($p3.Value)" }
        } catch { }
      }
    }
    if ($ts.Length -lt 10) { continue }
    if ($ts.Substring(0,10) -ne $today) { continue }

    # signals heuristic
    $sig = ""
    $pSig = $o.PSObject.Properties["signal"]
    if ($null -ne $pSig -and $null -ne $pSig.Value) { $sig = "$($pSig.Value)" }
    $side = ""
    $pSide = $o.PSObject.Properties["side"]
    if ($null -ne $pSide -and $null -ne $pSide.Value) { $side = "$($pSide.Value)" }
    if (-not [string]::IsNullOrWhiteSpace($sig) -or -not [string]::IsNullOrWhiteSpace($side)) { $nSignals++ }

    # realized pnl samples (presence-based)
    if ($o.PSObject.Properties.Name -contains "realized_pnl") {
      $nPnL++
    }

    if ($o.PSObject.Properties.Name -contains "edge_ratio") {
      try { $sumEdge += [double]$o.edge_ratio; $nEdge++ } catch {}
    }
    if ($o.PSObject.Properties.Name -contains "micro_score") {
      try { $sumMicro += [double]$o.micro_score; $nMicro++ } catch {}
    }
  }

  if ($nSignals -lt 1) { return $false }

  $meanEdge = 0.0; if ($nEdge -gt 0) { $meanEdge = $sumEdge / [double]$nEdge }
  $meanMicro = 0.0; if ($nMicro -gt 0) { $meanMicro = $sumMicro / [double]$nMicro }

  $header = "as_of_date,symbol,source,count_signals,pnl_samples,mean_edge_ratio,mean_micro_score"
  $row = "{0},{1},{2},{3},{4},{5},{6}" -f $today,"NVDA","REAL_PROXY",$nSignals,$nPnL,([Math]::Round($meanEdge,6)),([Math]::Round($meanMicro,6))

  $header | Out-File -FilePath $out -Encoding ascii
  $row    | Add-Content -Path $out -Encoding ascii
  return $true
}

$out   = Join-Path $logs ("gatescore_daily_summary_{0}.csv" -f $Symbol.ToLowerInvariant())
# Fail-closed: we prefer real inputs. If none found, we write HEADER ONLY (no today row).
$symLower = $Symbol.ToLowerInvariant()
$candidates = @(
  (Join-Path $logs "gatescore_events.jsonl"),
  (Join-Path $logs ("{0}_gatescore_events.jsonl" -f $symLower)),
  (Join-Path $logs "gatescore_samples.csv"),
  (Join-Path $logs ("{0}_gatescore_samples.csv" -f $symLower))
)

$input = $null
foreach($c in $candidates){
  if(Test-Path $c){ $input = $c; break }
}

# REAL mode fallback: if samples exist but are stale, try build today row from nvda_phase5_paperlive_results.jsonl
if ($Mode -eq "REAL" -and $input -like "*nvda_gatescore_samples.csv" -and -not (Has-TodayLine $input $today)) {
  $ok = Try-BuildRealFromNvdaPaperlive -repoRoot $repoRoot -logs $logs -today $today -out $out
  if ($ok) {
    Write-Host ("[GATESCORE] REAL paperlive fallback wrote {0}" -f $out) -ForegroundColor Green
    Get-Content $out -TotalCount 2
    exit 0
  } else {
    Write-Host "[GATESCORE] WARN: REAL paperlive fallback could not produce today row; continue fail-closed." -ForegroundColor Yellow
  }
}
if (-not $input) {
  # Header only -> Build-BlockGStatusStub will set gatescore_fresh_today=false => nvda_blockg_ready=false
  "as_of_date,symbol,source,count_signals,pnl_samples,mean_edge_ratio,mean_micro_score" | Out-File -FilePath $out -Encoding ascii
  Write-Host "[GATESCORE] WARN: no GateScore input found; wrote header-only logs\gatescore_daily_summary.csv (fail-closed)." -ForegroundColor Yellow
  exit 0
}

$py = Join-Path $repoRoot ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "[GATESCORE] ERROR: missing .venv python at $py" -ForegroundColor Red; exit 2 }

$calc = Join-Path $repoRoot "tools\compute_gatescore_daily_summary.py"
if (-not (Test-Path $calc)) { Write-Host "[GATESCORE] ERROR: missing $calc" -ForegroundColor Red; exit 3 }

Write-Host "[GATESCORE] Using input: $input" -ForegroundColor Cyan

# --- REAL JSONL aggregation path (skip python calculator) ---
try {
  if ($input -like "*_gatescore_events.jsonl") {
    $evts = @()
    Get-Content $input -Encoding utf8 | ForEach-Object {
      if ($_ -and $_.Trim()) {
        try { $evts += ($_ | ConvertFrom-Json -ErrorAction Stop) } catch { }
      }
    }

    if ($evts.Count -gt 0 -and ($evts[0].PSObject.Properties.Name -contains "edge_ratio")) {
      $sumSignals = 0
      $sumPnls    = 0
      $sumEdge    = 0.0
      $sumMicro   = 0.0
      $n          = 0

      foreach ($e in $evts) {
        try {
          $sumSignals += [int]$e.count_signals
          $sumPnls    += [int]$e.pnl_samples
          $sumEdge    += [double]$e.edge_ratio
          $sumMicro   += [double]$e.micro_score
          $n++
        } catch { }
      }

      if ($n -gt 0) {
        $header = "as_of_date,symbol,source,count_signals,pnl_samples,mean_edge_ratio,mean_micro_score"
        $row = "{0},{1},{2},{3},{4},{5},{6}" -f `
          $today,$Symbol,(Get-GateScoreSourceFromMode $Mode),`
          $sumSignals,$sumPnls,`
          ([Math]::Round($sumEdge / $n,6)),`
          ([Math]::Round($sumMicro / $n,6))

        $header | Out-File -FilePath $out -Encoding ascii
        $row    | Add-Content -Path $out -Encoding ascii

        Write-Host ("[GATESCORE] REAL JSONL aggregation wrote {0}" -f $out) -ForegroundColor Green
        Get-Content $out -TotalCount 2
        exit 0
      }
    }
  }
} catch {
  Write-Host ("[GATESCORE] WARN: REAL JSONL aggregation failed: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
}
# --- end REAL JSONL aggregation ---


# --- Minimal JSONL fallback (schema-safe) -------------------------------------
# If input is *_gatescore_events.jsonl with only count_signals/pnl_samples/score,
# the Python calculator may emit empty/skip. We aggregate deterministically here.
try {
  $ext = [IO.Path]::GetExtension($input).ToLowerInvariant()
  $name = [IO.Path]::GetFileName($input).ToLowerInvariant()
  if ($ext -eq ".jsonl" -and $name -like "*_gatescore_events.jsonl") {
    $rawLines = @(Get-Content -LiteralPath $input -ErrorAction Stop)
    $evts = @()
    foreach ($ln in $rawLines) {
      if ([string]::IsNullOrWhiteSpace($ln)) { continue }
      try { $evts += ($ln | ConvertFrom-Json -ErrorAction Stop) } catch { }
    }
    if ($evts.Count -gt 0) {
      $missingEdge = $true; $missingMicro = $true
      foreach ($e in $evts) {
        if ($e.PSObject.Properties.Name -contains "edge_ratio") { $missingEdge = $false }
        if ($e.PSObject.Properties.Name -contains "micro_score") { $missingMicro = $false }
      }
      if ($missingEdge -and $missingMicro) {
        $sumSignals = 0; $sumPnls = 0; $sumScore = 0.0; $n = 0
        foreach ($e in $evts) {
          try { $sumSignals += [int]$e.count_signals } catch { }
          try { $sumPnls    += [int]$e.pnl_samples } catch { }
          try { $sumScore   += [double]$e.score } catch { }
          $n++
        }
        $meanScore = 0.0
        if ($n -gt 0) { $meanScore = $sumScore / [double]$n }
        $src = Get-GateScoreSourceFromMode $Mode
        $header2 = "as_of_date,symbol,source,count_signals,pnl_samples,mean_edge_ratio,mean_micro_score"
        $d = "$today"
        $lines2 = @(
          $header2,
          ("{0},{1},{2},{3},{4},{5},{6}" -f $d,$Symbol,$src,$sumSignals,$sumPnls,("{0:F6}" -f $meanScore),("{0:F6}" -f 0.0))
        )
        $lines2 | Out-File -FilePath $out -Encoding ascii
        Write-Host ("[GATESCORE] Minimal JSONL fallback wrote {0}" -f $out) -ForegroundColor Green
        Get-Content $out -TotalCount 2
        exit 0
      }
    }
  }
} catch {
  Write-Host ("[GATESCORE] WARN: minimal JSONL fallback failed: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
}
# -----------------------------------------------------------------------------

& $py $calc $input $out
$code = $LASTEXITCODE
if ($code -ne 0) {
  Write-Host "[GATESCORE] ERROR: calculator failed (exit=$code). Fail-closed." -ForegroundColor Red
  exit $code
}


# Convert daily summary schema (as_of_date,samples,score) -> BlockG schema expected by Build-BlockGStatusStub
try {
  $rows = @(Import-Csv -LiteralPath $out)
} catch { $rows = @() }

# Rewrite output with BlockG schema
$header2 = "as_of_date,symbol,source,count_signals,pnl_samples,mean_edge_ratio,mean_micro_score"
if (-not $rows) {
  $header2 | Out-File -FilePath $out -Encoding ascii
} else {
  $sym = $Symbol
  $inPath = $null
  foreach($vn in @("input","Input","InputCsv","inputCsv","inputPath","InputPath","samplesCsv","SamplesCsv")) {
    $v = Get-Variable -Name $vn -ErrorAction SilentlyContinue
    if ($v -and $v.Value) { $inPath = ($v.Value + ""); break }
  }
  $src = Get-GateScoreSourceFromMode $Mode
  $lines = @($header2)
  foreach($r in $rows) {
    $d = "$($r.as_of_date)"
    if ($d.Length -ge 10) { $d = $d.Substring(0,10) }
    $n = 0
    try { $n = [int]("$($r.samples)") } catch { $n = 0 }

    $sc = 0.0
    try { $sc = [double]("$($r.score)") } catch { $sc = 0.0 }

    # Prefer real counts if present (single-pass deterministic), else fallback to samples proxy
    $cs = $n
    $ps = $n
    if ($r.PSObject.Properties.Name -contains "count_signals") {
      try { $cs = [int]("$($r.count_signals)") } catch { $cs = $n }
    }
    if ($r.PSObject.Properties.Name -contains "pnl_samples") {
      try { $ps = [int]("$($r.pnl_samples)") } catch { $ps = $n }
    }

    # mean_micro_score placeholder 0.0 until real metric wired
    $lines += ("{0},{1},{2},{3},{4},{5},{6}" -f $d,$sym,$src,$cs,$ps,("{0:F6}" -f $sc),("{0:F6}" -f 0.0))
  }
  $lines | Out-File -FilePath $out -Encoding ascii
}

# Visibility: show top 2 lines
Write-Host ("[GATESCORE] Wrote {0}" -f $out) -ForegroundColor Green
Get-Content $out -TotalCount 2
exit 0










# --- GATESCORE_MASTER_UPSERT ---
try {
  $master = Join-Path $logs "gatescore_daily_summary.csv"
  if(-not (Test-Path $master)){
    "as_of_date,symbol,source,count_signals,pnl_samples,mean_edge_ratio,mean_micro_score" | Out-File -FilePath $master -Encoding ascii
  }

  $today = (Get-Date).ToString("yyyy-MM-dd")
  $sym = ("$Symbol").Trim().ToUpperInvariant()

  if(Test-Path $out){
    $lines = Get-Content $out -Encoding utf8
    if($lines.Count -ge 2){
      $row = $lines[-1]
      if($row -like "$today,*"){
        $m = Get-Content $master -Encoding utf8
        $m = $m | Where-Object { $_ -notlike "$today,$sym,*" }
        $m += $row

        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($master, ($m -join "`n"), $utf8NoBom)

        Write-Host "[GATESCORE] Master upserted: $row" -ForegroundColor Green
      }
    }
  }
} catch {
  Write-Host "[GATESCORE] WARN: master upsert failed (non-fatal): $($_.Exception.Message)" -ForegroundColor Yellow
}
# --- END GATESCORE_MASTER_UPSERT ---