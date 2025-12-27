[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [string]$Config = "config/config.yaml",

  # Loop controls
  [int]$Ticks = 0,
  [double]$SleepSec = 0.25,

  # IB snapshots attempt (Option A still safe because runner can fallback)
  [switch]$UseIBSnapshots,

  # Always log
  [string]$LogFile = "auto"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot "logs") | Out-Null

# Resolve config absolute
$cfgAbs = $Config
if(-not [System.IO.Path]::IsPathRooted($cfgAbs)){
  $cfgAbs = Join-Path $repoRoot $cfgAbs
}
if(Test-Path -LiteralPath $cfgAbs){
  $cfgAbs = (Resolve-Path -LiteralPath $cfgAbs).Path
}

# ---- PRE-FLIGHT GATES (fail-closed) ----
Write-Host "[OPS] Preflight starting..." -ForegroundColor Cyan

# Paper hard-set
$env:HAT_IS_PAPER = "1"
# Ensure our repo src wins
$env:PYTHONPATH = (Resolve-Path (Join-Path $repoRoot "src")).Path

# Fresh Block-G
Remove-Item Env:HAT_BLOCKG_BUILT_ONCE -ErrorAction SilentlyContinue
& (Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1")

# ---- Block-G READY check (fail-closed) ----
$statusPath = Join-Path $repoRoot "logs\blockg_status_stub.json"
if(-not (Test-Path -LiteralPath $statusPath)){ throw "[OPS] Missing Block-G status stub: $statusPath" }
$bg = Get-Content $statusPath -Raw -Encoding utf8 | ConvertFrom-Json
$k = ($Symbol.ToLower() + "_blockg_ready")
if(-not ($bg.PSObject.Properties.Name -contains $k)){ throw "[OPS] Block-G key missing: $k" }
if(-not [bool]$bg.$k){
  $reasons = $bg.reasons_not_ready
  Write-Host "[OPS] BLOCK-G NOT READY. reasons_not_ready:" -ForegroundColor Red
  try { $reasons | ConvertTo-Json -Depth 6 | Out-Host } catch { $reasons | Out-Host }
  throw "[OPS] Preflight failed: Block-G not ready for $Symbol"
}
Write-Host "[OPS] Block-G READY for $Symbol" -ForegroundColor Green


# Risk slice
& (Join-Path $repoRoot "tools\python.ps1") -m pytest -q (Join-Path $repoRoot "tests") -k "blockg or risk or phase5"
if($LASTEXITCODE -ne 0){ throw "[OPS] Preflight failed: pytest risk slice not green." }

# Optional Phase-6 snapshot (best-effort)
try { & (Join-Path $repoRoot "tools\Build-Phase6PortfolioState.ps1") } catch {}

Write-Host "[OPS] Preflight OK." -ForegroundColor Green

# ---- DETACHED RUN ----
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ throw "Missing venv python: $py" }

$day = (Get-Date).ToString("yyyy-MM-dd")
$stdout = Join-Path $repoRoot ("logs\paper_live_{0}_{1}.stdout.txt" -f $Symbol,$day)
$stderr = Join-Path $repoRoot ("logs\paper_live_{0}_{1}.stderr.txt" -f $Symbol,$day)

$args = @(
  "-m","hybrid_ai_trading.runners.paper_runner",
  "--config",$cfgAbs,
  "--universe",$Symbol,
  "--ticks",$Ticks.ToString(),
  "--sleep-sec",$SleepSec.ToString(),
  "--log-file",$LogFile
)

if($UseIBSnapshots){ $args += @("--ib-snapshots") }

$cmdLine = "$py " + ($args -join " ")

Write-Host "[OPS] Starting detached paper-live..." -ForegroundColor Cyan
Write-Host "[OPS] $cmdLine" -ForegroundColor DarkGray

$p = Start-Process -FilePath $py `
  -ArgumentList $args `
  -WorkingDirectory $repoRoot `
  -WindowStyle Minimized `
  -RedirectStandardOutput $stdout `
  -RedirectStandardError $stderr `
  -PassThru

# Write PID file
$pidPath = Join-Path $repoRoot "logs\paper_live_pid.json"
$rec = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  symbol = $Symbol
  pid = $p.Id
  config = $cfgAbs
  use_ib_snapshots = [bool]$UseIBSnapshots
  ticks = $Ticks
  sleep_sec = $SleepSec
  log_file = $LogFile
  stdout = $stdout
  stderr = $stderr
  cmd = $cmdLine
}
$rec | ConvertTo-Json -Depth 6 | Out-File $pidPath -Encoding utf8

Write-Host "[OPS] STARTED pid=$($p.Id)" -ForegroundColor Green
Write-Host "[OPS] PID file: $pidPath" -ForegroundColor DarkGray
