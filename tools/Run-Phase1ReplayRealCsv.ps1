[CmdletBinding()]
param(
  [Parameter(Mandatory)]
  [string]$InputCsv,

  [string]$Config = "config/paper_runner.yaml",
  [string]$Symbol = "NVDA",
  [string]$StartDate = "",
  [string]$EndDate = "",
  [string]$OutDir = "logs\replay",
  [int]$Batch = 100
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

if (-not (Test-Path -LiteralPath $InputCsv)) { throw "Phase1 REAL replay: InputCsv missing: $InputCsv" }
$lines = Get-Content -LiteralPath $InputCsv -Encoding UTF8
if (-not $lines -or $lines.Count -lt 2) { throw "Phase1 REAL replay: InputCsv empty/too small (need header+rows): $InputCsv" }

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Python missing: $py" }
$env:PYTHONPATH = Join-Path $repoRoot "src"

# Ensure outdir
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Force -Path $OutDir | Out-Null }

# Run the existing REAL replay engine (csv -> run_once batches)
$btLog = Join-Path $OutDir "backtest_real.jsonl"
& $py -m hybrid_ai_trading.runners.backtest_replay --config $Config --input $InputCsv --log $btLog --batch $Batch
$code = $LASTEXITCODE
if ($code -ne 0) { exit $code }

# Produce Phase1 session artifact (REAL)
$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

if (-not $StartDate) { $StartDate = $today }
if (-not $EndDate)   { $EndDate   = $today }

$session = [ordered]@{
  ts_utc = $tsUtc
  as_of_date = $today
  symbol = $Symbol.ToUpperInvariant()
  window = [ordered]@{
    start_date = $StartDate
    end_date   = $EndDate
    start_time_local = "09:30:00"
    end_time_local   = "16:00:00"
  }
  fill_model = "deterministic_fee1.0_slip2.0"
  latency_model = "deterministic_130ms"
  bars_source = "csv"
  bars_path = $InputCsv
  notes = "REAL Phase1 replay via runners.backtest_replay (csv snapshots -> run_once)"
}

# Write JSON UTF8-noBOM
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$sessionPath = Join-Path $repoRoot (Join-Path $OutDir "replay_session.json")
[System.IO.File]::WriteAllText($sessionPath, ($session | ConvertTo-Json -Depth 8) + "`n", $utf8NoBom)

Write-Host "[PHASE1-REAL] wrote $sessionPath" -ForegroundColor Green
Write-Host "[PHASE1-REAL] wrote $btLog" -ForegroundColor Green

exit 0