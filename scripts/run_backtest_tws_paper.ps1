[CmdletBinding()]
param(
  [int]$ClientId = 3021,
  [int]$WaitListenSec = 120,
  [int]$HandshakeTimeoutMs = 2500,
  [string]$PythonRel   = ".\.venv\Scripts\python.exe",
  [string]$BacktestRel = "hybrid_ai_trading\pipelines\backtest.py",
  [string]$RepoRoot = $null,
  [switch]$PauseOnExit,
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
  param([string]$ProvidedRoot)
  if ($ProvidedRoot -and (Test-Path $ProvidedRoot)) { return (Resolve-Path $ProvidedRoot).Path }
  $scriptPath = $null; try { $scriptPath = $MyInvocation.MyCommand.Path } catch {}
  if ($scriptPath -and (Test-Path $scriptPath)) { return (Split-Path -Parent (Split-Path -Parent $scriptPath)) }
  if ($PSScriptRoot -and (Test-Path $PSScriptRoot)) { return (Split-Path -Parent $PSScriptRoot) }
  return (Get-Location).Path
}

$RepoRoot = Get-RepoRoot -ProvidedRoot $RepoRoot
Set-Location $RepoRoot

$Python   = Resolve-Path -LiteralPath $PythonRel   -ErrorAction SilentlyContinue
$Backtest = Resolve-Path -LiteralPath $BacktestRel -ErrorAction SilentlyContinue
if (-not $Backtest) {
  Write-Host "🔎 Scanning repo for backtest.py ..." -ForegroundColor DarkYellow
  $found = Get-ChildItem $RepoRoot -Recurse -File -Filter backtest.py -ErrorAction SilentlyContinue |
           Select-Object -First 1 -ExpandProperty FullName
  if ($found) { $Backtest = $found; Write-Host "📄 Auto-selected backtest: $Backtest" -ForegroundColor DarkYellow }
}

Write-Host "Repo root : $RepoRoot"
Write-Host "Python    : $Python"
Write-Host "Backtest  : $Backtest"

if (-not $Python)   { Write-Host "❌ Python not found at $PythonRel" -ForegroundColor Yellow; if($PauseOnExit){Read-Host "Press Enter"}; exit 3 }
if (-not $Backtest) { Write-Host "❌ backtest.py not found (tried $BacktestRel + auto-scan)" -ForegroundColor Yellow; if($PauseOnExit){Read-Host "Press Enter"}; exit 4 }

# 1) Start TWS Paper if not running
$twspath = Get-ChildItem 'C:\Jts\TWS' -Recurse -Filter tws.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
if (-not (Get-Process tws -ErrorAction SilentlyContinue)) {
  if ($twspath) { Write-Host "▶ Starting TWS Paper: $twspath"; Start-Process $twspath; Start-Sleep 8 }
  else { Write-Host "❌ Could not find tws.exe under C:\Jts\TWS" -ForegroundColor Yellow; if($PauseOnExit){Read-Host "Press Enter"}; exit 5 }
}

# 2) Wait for 7497 LISTEN
$deadline = (Get-Date).AddSeconds($WaitListenSec)
$listenOK = $false
do {
  Start-Sleep -Milliseconds 500
  try { if (Get-NetTCPConnection -State Listen -LocalPort 7497 -ErrorAction SilentlyContinue) { $listenOK = $true } } catch {}
} until ($listenOK -or (Get-Date) -ge $deadline)

if (-not $listenOK) {
  Write-Host "❌ TWS Paper API NOT READY (7497 not listening within $WaitListenSec s)" -ForegroundColor Yellow
  netstat -ano | Select-String ":7497" | Out-Host
  if($PauseOnExit){Read-Host "Press Enter"}; exit 1
}

Write-Host "✔ 7497 is LISTENING" -ForegroundColor Green
(Get-NetTCPConnection -State Listen -LocalPort 7497) | ForEach-Object { Get-Process -Id $_.OwningProcess } | Select Name,Id,Path | Format-Table | Out-String | Write-Host

# 3) Choose host (simple, robust): try IPv6 loopback then fallback to IPv4
$chosenHost = '::1'
try {
  $tcp = New-Object System.Net.Sockets.TcpClient
  $tcp.ReceiveTimeout = 750; $tcp.SendTimeout = 750
  $tcp.Connect('::1', 7497)
  $tcp.Close()
} catch {
  $chosenHost = 'localhost'
}
Write-Host ("✅ Using {0}:7497" -f $chosenHost) -ForegroundColor Green

# 4) Export env + run backtest (pass-thru args)
$env:IB_HOST      = $chosenHost
$env:IB_PORT      = "7497"
$env:IB_CLIENT_ID = "$ClientId"

Write-Host "▶ Running backtest..." -ForegroundColor Cyan
$pyOutput = & $Python $Backtest @Args 2>&1
$code = $LASTEXITCODE

Write-Host "----- backtest output (begin) -----"
if ($pyOutput) { $pyOutput | ForEach-Object { $_ | Out-Host } } else { Write-Host "(no output)" }
Write-Host "----- backtest output (end) -------"
Write-Host ("backtest exit code = {0}" -f $code)

if ($PauseOnExit) { Read-Host "Press Enter to close" }
exit $code
