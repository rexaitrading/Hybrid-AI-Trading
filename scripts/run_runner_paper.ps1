param(
  [bool]  $Once       = $true,      # usage: -Once $false  (omit => one-shot)
  [string]$Config     = "config\paper_runner.yaml",
  [int]   $Mdt        = 3,
  [string]$LogFile    = "logs\runner_paper.jsonl",
  [string]$Universe   = "",
  [bool]  $WaitForPort= $true,      # wait until an API port opens
  [int]   $WaitSec    = 300         # wait up to 300s
)

$ErrorActionPreference = 'Stop'

# ----- resolve repo root (works as file or pasted inline) -----
$scriptPath = $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($scriptPath)) { $scriptDir = (Get-Location).Path } else { $scriptDir = Split-Path -Parent $scriptPath }
$leaf = Split-Path -Leaf $scriptDir
if ($leaf -eq 'scripts') { $repo = Split-Path -Parent $scriptDir } else {
  if (Test-Path (Join-Path $scriptDir 'scripts')) { $repo = $scriptDir } else { $repo = (Get-Location).Path }
}
Push-Location $repo

# ----- env / dirs -----
$env:PYTHONPATH = "src"
$logDir = Split-Path -Parent $LogFile
if ($logDir -and -not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" -Force | Out-Null }

# ----- venv python -----
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  Write-Host "venv python not found: $py" -ForegroundColor Red
  Pop-Location; exit 3
}

# ----- candidate ports (env first, then 4003->4002->7497) -----
$ports = @()
if ($env:IB_PORT) { try { $ports += [int]$env:IB_PORT } catch {} }
$ports += 4003,4002,7497 | Select-Object -Unique

function Test-Port([int]$p){
  try {
    (Test-NetConnection 127.0.0.1 -Port $p -WarningAction SilentlyContinue).TcpTestSucceeded
  } catch { $false }
}

# ----- find (or wait for) an open port -----
$chosen = $null
$start  = Get-Date
do {
  foreach ($p in $ports) { if (Test-Port $p) { $chosen = $p; break } }
  if ($chosen) { break }
  if (-not $WaitForPort) {
    Write-Host "No IB API port open (tried: $($ports -join ', ')). Start IB Gateway Paper (4003/4002) or TWS Paper (7497)." -ForegroundColor Yellow
    Pop-Location; exit 2
  }
  $elapsed = (Get-Date) - $start
  if ($elapsed.TotalSeconds -ge $WaitSec) {
    Write-Host "Timed out waiting for IB API port (tried: $($ports -join ', '))." -ForegroundColor Yellow
    Pop-Location; exit 2
  }
  $remain = [int]($WaitSec - $elapsed.TotalSeconds)
  Write-Host (". waiting for IB API port to open (tried: {0}) â€” {1}s left" -f ($ports -join ', '), $remain) -ForegroundColor DarkYellow
  Start-Sleep -Seconds 2
} while (-not $chosen)

$env:IB_PORT = "$chosen"
Write-Host "Using IB API port: $chosen" -ForegroundColor Cyan

# ----- build arg array (each token separate; avoids the ' -m' bug) -----
$pyArgs = @(
  '-m','hybrid_ai_trading.runners.runner_paper',
  '--config',   $Config,
  '--mdt',      $Mdt.ToString(),
  '--log-file', $LogFile,
  '--json'
)
 += @('--client-id', .ToString())

if ($Once)      { $pyArgs += '--once' }
if ($Universe)  { $pyArgs += @('--universe', $Universe) }

# ----- run -----
& $py @pyArgs
$exit = $LASTEXITCODE

# ----- tail logs on one-shot -----
if ($Once) {
  if (Test-Path $LogFile) { Write-Host "`n--- Tail of $LogFile ---`n"; Get-Content $LogFile -Tail 20 }
  $audit = "logs\paper_trades.jsonl"
  if (Test-Path $audit) { Write-Host "`n--- Tail of $audit ---`n"; Get-Content $audit -Tail 20 }
  else { Write-Host "`n(no audit yet â€” appears after first evaluation pass inside a trading window)" -ForegroundColor Yellow }
}

Pop-Location
exit $exit
