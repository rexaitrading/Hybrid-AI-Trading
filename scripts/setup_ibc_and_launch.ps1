param([int]$PortWaitSec = 120)
$ErrorActionPreference = 'Stop'
Write-Host "[setup_ibc_and_launch] start" -ForegroundColor Cyan

# Verify IBG 1039 exists
$gwExe = 'C:\Jts\ibgateway\1039\ibgateway.exe'
if (!(Test-Path $gwExe)) { throw "Missing: $gwExe (install/restore IB Gateway 1039 first)" }

# Verify IBC exists
$ibcExe = $null
if (Test-Path 'C:\IBC\IBC.exe') { $ibcExe = 'C:\IBC\IBC.exe' }
elseif (Test-Path 'C:\IBC\IBController.exe') { $ibcExe = 'C:\IBC\IBController.exe' }
if (-not $ibcExe) {
  Write-Host "Ã¢Ââ€” IBC not found under C:\IBC. Unzip the IBC Windows ZIP to C:\IBC then re-run." -ForegroundColor Yellow
  exit 1
}

# IBC config (Paper + auto-accept + 4002)
$cfg = "$env:USERPROFILE\Documents\IBC\config.ini"
$cfgDir = Split-Path $cfg
if (!(Test-Path $cfgDir)) { New-Item -ItemType Directory -Path $cfgDir -Force | Out-Null }
@"
FIX=no
TradingMode=paper
AcceptNonBrokerageAccountWarning=yes
AcceptIncomingConnectionAction=accept
OverrideTwsApiPort=4002
"@ | Set-Content -LiteralPath $cfg -Encoding ASCII
Write-Host "IBC config -> $cfg" -ForegroundColor Green

# Force-pinned BAT (ignores outer env; pins 1039/path)
$logDir = 'C:\HybridAI\logs'
if (!(Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$bat = 'C:\IBC\StartGateway_1039_FORCE.bat'
@"
@echo off
setlocal
set TWS_MAJOR_VRSN=1039
set TWS_PATH=C:\Jts\ibgateway\1039
set IBC_INI=%USERPROFILE%\Documents\IBC\config.ini
set LOG_PATH=$logDir
if not exist "%LOG_PATH%" mkdir "%LOG_PATH%"
set IBC_EXE=$ibcExe
start "" "%IBC_EXE%" --gateway --ib-dir "%TWS_PATH%" --mode paper --ibc-ini "%IBC_INI%" --tws-version %TWS_MAJOR_VRSN% --log-dir "%LOG_PATH%"
timeout /t 2 >nul
tasklist | find /I "ibgateway.exe" >nul && goto :done
start "" "%IBC_EXE%" "--gateway" "--tws-path=%TWS_PATH%" "--mode=paper" "--ibc-ini=%IBC_INI%" "--tws-version=%TWS_MAJOR_VRSN%" "--log-dir=%LOG_PATH%"
:done
endlocal
"@ | Set-Content -LiteralPath $bat -Encoding ASCII
Write-Host "Launcher -> $bat" -ForegroundColor Green

# Kill strays and launch minimized
taskkill /F /IM ibgateway.exe /IM java.exe /IM IBC.exe /IM IBController.exe 2>$null | Out-Null
Start-Process -WindowStyle Minimized -FilePath $bat

# Wait for Paper port 4002
$deadline = (Get-Date).AddSeconds($PortWaitSec)
do {
  Start-Sleep -Milliseconds 500
  $open = (Test-NetConnection 127.0.0.1 -Port 4002 -WarningAction SilentlyContinue).TcpTestSucceeded
} until ($open -or (Get-Date) -ge $deadline)
if (-not $open) { throw "Port 4002 did not open in $PortWaitSec s. If a login window is waiting, complete PAPER login once and re-run." }

# Show owner (java.exe is normal when IBC launches)
$own = (Get-NetTCPConnection -LocalPort 4002 -State Listen -ErrorAction SilentlyContinue).OwningProcess
if ($own) { Get-Process -Id $own | Select Name,Id,Path | Format-Table -AutoSize }

# Handshake (>0 bytes confirms API armed)
$client = New-Object System.Net.Sockets.TcpClient
$client.ReceiveTimeout=2000; $client.SendTimeout=2000
$client.Connect('127.0.0.1',4002)
$s=$client.GetStream(); $enc=[Text.Encoding]::ASCII
$s.Write($enc.GetBytes("API`0"),0,4)
$b=New-Object byte[] 64; $n=$s.Read($b,0,64)
Write-Host "$n bytes from handshake" -ForegroundColor Cyan
$client.Close()

# venv probe
$py = ".\.venv\Scripts\python.exe"
if (Test-Path $py) {
@'
from ib_insync import *
ib=IB()
ok=ib.connect("127.0.0.1",4002,clientId=3021,timeout=45)
print("Connected:", bool(ok))
if ok:
    print("Time:", ib.reqCurrentTime())
    ib.disconnect()
'@ | & $py -
} else {
  Write-Host "venv python not found at $py; adjust if needed." -ForegroundColor Yellow
}

Write-Host "[setup_ibc_and_launch] done" -ForegroundColor Cyan
