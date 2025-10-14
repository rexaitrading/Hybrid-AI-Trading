param(
  [int]$ClientId = 3021,
  [int]$PortWaitSec  = 45,   # wait for TCP port
  [int]$ApiWaitSec   = 60    # wait for API handshake (after login)
)

$ErrorActionPreference = 'Stop'

$gw  = "C:\Jts\ibgateway\1039\ibgateway.exe"
$ini = "C:\Jts\ibgateway\1039\jts.ini"

if (!(Test-Path $gw)) { throw "Not found: $gw" }
if (!(Test-Path $ini)) { throw "Not found: $ini" }

# Ensure API keys exist in jts.ini (won't duplicate)
$txt = Get-Content $ini -Raw
if ($txt -notmatch '^\s*ApiOnly\s*='         ) { $txt += "`r`nApiOnly=true" }
if ($txt -notmatch '^\s*SocketClient\s*='    ) { $txt += "`r`nSocketClient=1" }
if ($txt -notmatch '^\s*SocketClientPort\s*=') { $txt += "`r`nSocketClientPort=4002" }
Set-Content $ini -Value $txt -Encoding ASCII

# If 4002 is already listening, reuse the existing session (no restart)
$already = (Test-NetConnection 127.0.0.1 -Port 4002 -WarningAction SilentlyContinue).TcpTestSucceeded
if (-not $already) {
  # If process not running, start it. Do NOT kill existing sessions.
  if (-not (Get-Process ibgateway -ErrorAction SilentlyContinue)) {
    Write-Host "Starting IB Gateway..." -ForegroundColor Yellow
    Start-Process $gw -WorkingDirectory (Split-Path $gw)
  } else {
    Write-Host "IB Gateway process is running but 4002 is not up yet." -ForegroundColor Yellow
  }

  # Give user a hint to log in if needed
  Write-Host "If login is required, switch to the IB Gateway window and log in to PAPER." -ForegroundColor Cyan
  Write-Host "Waiting for TCP port 4002 to open..." -ForegroundColor DarkCyan

  $deadline = (Get-Date).AddSeconds($PortWaitSec)
  do {
    Start-Sleep -Milliseconds 500
    $already = (Test-NetConnection 127.0.0.1 -Port 4002 -WarningAction SilentlyContinue).TcpTestSucceeded
  } until ($already -or (Get-Date) -ge $deadline)

  if (-not $already) { throw "Port 4002 did not open within ${PortWaitSec}s." }
}

# Extra: wait for real API handshake (send 'API\0' and expect bytes back)
function Test-IbApiReady {
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $client.ReceiveTimeout = 1500; $client.SendTimeout = 1500
    $client.Connect('127.0.0.1',4002)
    $stream = $client.GetStream()
    $enc = [System.Text.Encoding]::ASCII
    $hello = $enc.GetBytes("API`0")
    $stream.Write($hello,0,$hello.Length)
    $buf = New-Object byte[] 64
    $read = $stream.Read($buf,0,$buf.Length)
    $client.Close()
    return ($read -gt 0)
  } catch { return $false }
}

Write-Host "Waiting for IB API handshake (you may need to accept any dialogs the first time)..." -ForegroundColor DarkCyan
$apiDeadline = (Get-Date).AddSeconds($ApiWaitSec)
$apiReady = $false
do {
  Start-Sleep -Milliseconds 800
  $apiReady = Test-IbApiReady
} until ($apiReady -or (Get-Date) -ge $apiDeadline)

if (-not $apiReady) {
  throw "API handshake on 4002 did not become ready within ${ApiWaitSec}s. Check Gateway for pop-ups (paper warning, market-data notice, incoming-connection)."
}

# Run probe with correct env
$env:IB_HOST      = "127.0.0.1"
$env:IB_PORT      = "4002"
$env:IB_CLIENT_ID = "$ClientId"

Write-Host "IB env: $($env:IB_HOST):$($env:IB_PORT) (clientId=$($env:IB_CLIENT_ID))" -ForegroundColor Cyan
.\.venv\Scripts\python.exe scripts\probe_ib_api.py
