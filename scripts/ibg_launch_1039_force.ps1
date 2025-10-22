param([int]$WaitSec = 90)
$ErrorActionPreference = 'Stop'

# 1) Kill stray processes (non-fatal if not running)
Get-Process ibgateway, java -ErrorAction SilentlyContinue | ForEach-Object {
  try { taskkill /PID $_.Id /F | Out-Null } catch {}
}

# 2) Launch the correct binary (NO reliance on env vars)
$gw = 'C:\Jts\ibgateway\1039\ibgateway.exe'
if (!(Test-Path $gw)) { throw "Not found: $gw" }
Start-Process $gw -WorkingDirectory (Split-Path $gw)

# 3) Wait for PAPER port 4002 to open
$deadline = (Get-Date).AddSeconds($WaitSec)
do {
  Start-Sleep -Milliseconds 500
  $ok = (Test-NetConnection 127.0.0.1 -Port 4002 -WarningAction SilentlyContinue).TcpTestSucceeded
} until ($ok -or (Get-Date) -ge $deadline)

if (-not $ok) {
  Write-Host ">>> ACTION: Switch to Gateway and complete PAPER login, then re-run this script." -ForegroundColor Yellow
  exit 1
}

# 4) Show owner for sanity
$own = (Get-NetTCPConnection -LocalPort 4002 -State Listen -ErrorAction SilentlyContinue).OwningProcess
if ($own) { Get-Process -Id $own | Select Name,Id,Path | Format-Table -AutoSize }
Write-Host "IBG 1039 PAPER is listening on 4002." -ForegroundColor Green
