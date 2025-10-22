param(
  [int]$WaitSec = 60
)

$ErrorActionPreference='Stop'
$gw = 'C:\Jts\ibgateway\1039\ibgateway.exe'
if (!(Test-Path $gw)) { throw "Not found: $gw" }

# Harden jts.ini (idempotent)
$ini = 'C:\Jts\ibgateway\1039\jts.ini'
$txt = Get-Content $ini -Raw
if ($txt -notmatch '^\s*ApiOnly\s*=')          { $txt += "`r`nApiOnly=true" }
if ($txt -notmatch '^\s*SocketClient\s*=')     { $txt += "`r`nSocketClient=1" }
if ($txt -notmatch '^\s*SocketClientPort\s*=') { $txt += "`r`nSocketClientPort=4002" }
Set-Content $ini -Value $txt -Encoding ASCII

# Kill strays from wrong locations
Get-Process ibgateway,java -ErrorAction SilentlyContinue | ForEach-Object {
  try { taskkill /PID $_.Id /F | Out-Null } catch {}
}

# Launch (Paper is chosen in the small chooser)
Start-Process $gw -WorkingDirectory (Split-Path $gw)

# Wait for 4002 to open
$deadline=(Get-Date).AddSeconds($WaitSec)
do {
  Start-Sleep -Milliseconds 500
  $ok=(Test-NetConnection 127.0.0.1 -Port 4002 -WarningAction SilentlyContinue).TcpTestSucceeded
} until ($ok -or (Get-Date) -ge $deadline)

if (-not $ok) {
  Write-Host ">>> ACTION: Switch to Gateway and complete PAPER login, then re-run this script." -ForegroundColor Yellow
  exit 1
}

# Show owner
$own=(Get-NetTCPConnection -LocalPort 4002 -State Listen -ErrorAction SilentlyContinue).OwningProcess
if ($own) { Get-Process -Id $own | Select Name,Id,Path | Format-Table -AutoSize }

Write-Host "IBG 1039 PAPER is listening on 4002." -ForegroundColor Green
