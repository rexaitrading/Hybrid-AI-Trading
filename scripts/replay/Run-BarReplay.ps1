param(
  [Parameter(Mandatory)][string]$CsvBars,       # e.g. .\data\SPY_1m_2025-10.csv
  [Parameter(Mandatory)][string]$Symbol,        # e.g. 'SPY'
  [int]$SpeedMs = 50,                           # bar playback speed (ms)
  [string]$Strategy = 'orb_scalper_v1',         # strategy key in Python
  [switch]$NoNotion                            # skip Notion writes
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

# --- Sanity: env for Notion & config ---
if (-not $env:NOTION_TOKEN -and -not $NoNotion) { throw "NOTION_TOKEN missing (use -NoNotion to dry-run)" }
if (-not $env:NOTION_DB_TRADES -and -not $NoNotion) { throw "NOTION_DB_TRADES missing (use -NoNotion to dry-run)" }

$DbId = if ($env:NOTION_DB_TRADES -and $env:NOTION_DB_TRADES.Length -eq 32) {
  $env:NOTION_DB_TRADES -replace '(.{8})(.{4})(.{4})(.{4})(.{12})','$1-$2-$3-$4-$5'
} else { $env:NOTION_DB_TRADES }

# --- Paths ---
$root = (Resolve-Path (git rev-parse --show-toplevel)).Path
$py   = Join-Path $root 'scripts\replay\bar_replay_runner.py'
if (-not (Test-Path $py)) { throw "Missing $py" }

# --- CSV existence check ---
if (-not (Test-Path $CsvBars)) { throw "CSV not found: $CsvBars" }

# --- Run replay (Python 3.12 venv assumed in PATH) ---
$env:PYTHONUTF8 = 1
if ($NoNotion) { $env:NO_NOTION = "1" } else { $env:NO_NOTION = $null }

$cmd = @(
  'python', $py,
  '--csv', $CsvBars,
  '--symbol', $Symbol,
  '--strategy', $Strategy,
  '--speed-ms', $SpeedMs
)
if (-not $NoNotion) {
  $cmd += @('--notion-db', $DbId)
}

Write-Host ">>> $($cmd -join ' ')" -ForegroundColor Cyan
$proc = Start-Process -FilePath $cmd[0] -ArgumentList $cmd[1..($cmd.Length-1)] -Wait -PassThru
if ($proc.ExitCode -ne 0) { throw "bar_replay_runner.py exit $($proc.ExitCode)" }
