param([switch]$ForceRestart,)

$ErrorActionPreference = "Stop"

Write-Host "[IBG] Killing any existing ibgateway/java..." -ForegroundColor Yellow
if($ForceRestart){ Stop-Process -Name ibgateway1 -Force -ErrorAction SilentlyContinue }
if($ForceRestart){ Stop-Process -Name ibgateway  -Force -ErrorAction SilentlyContinue }
if($ForceRestart){ Stop-Process -Name java       -Force -ErrorAction SilentlyContinue }
if($ForceRestart){ Stop-Process -Name javaw      -Force -ErrorAction SilentlyContinue }

Write-Host "[IBG] Starting IB Gateway 1040 (no IBC)...`n" -ForegroundColor Cyan
& "C:\Jts\ibgateway\1040\ibgateway1.exe"

Write-Host "`n[IBG] Launch command executed." -ForegroundColor Cyan
Write-Host "[IBG] If login window appeared, log in to PAPER and approve 2FA on IBKR Mobile." -ForegroundColor Green
Write-Host "[IBG] Keep this window open while trading." -ForegroundColor Green