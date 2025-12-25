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

$today = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
$out   = Join-Path $logs "gatescore_daily_summary.csv"

# Fail-closed: we prefer real inputs. If none found, we write HEADER ONLY (no today row).
$symLower = $Symbol.ToLowerInvariant()
$candidates = @(
  (Join-Path $logs "gatescore_events.jsonl"),
  (Join-Path $logs ("{0}_gatescore_events.jsonl" -f $symLower)),
  (Join-Path $logs "gatescore_samples.csv"),
  (Join-Path $logs ("{0}_gatescore_samples.csv" -f $symLower))
)$input = $null
foreach($c in $candidates){
  if(Test-Path $c){ $input = $c; break }
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
Write-Host "[GATESCORE] Wrote logs\gatescore_daily_summary.csv" -ForegroundColor Green
Get-Content $out -TotalCount 2
exit 0





