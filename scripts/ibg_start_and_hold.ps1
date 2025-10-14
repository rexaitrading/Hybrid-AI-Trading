param([int]$HoldSec = 30)
$ErrorActionPreference = 'Stop'

# Ensure IBG is up (waits for 4002 if needed)
powershell -ExecutionPolicy Bypass -File "scripts\ibg_launch_1039_force.ps1" -WaitSec 90 | Out-Null

# Resolve venv Python
$py = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (!(Test-Path $py)) { $py = ".\.venv\Scripts\python.exe" }
if (!(Test-Path $py)) { throw "venv python not found at .\.venv\Scripts\python.exe" }

# Keep API Client green
$code = @"
from ib_insync import *
ib = IB()
ib.connect('127.0.0.1', 4002, clientId=3021, timeout=45)
print('Connected:', True, 'Time:', ib.reqCurrentTime())
ib.sleep($HoldSec)
ib.disconnect()
"@
$code | & $py -
