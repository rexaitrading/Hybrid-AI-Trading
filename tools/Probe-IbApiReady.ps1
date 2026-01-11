[CmdletBinding()]
param(
  [string]$IbHost = "127.0.0.1",
  [int]$Port = 4002,
  [int]$ClientId = 3099,
  [int]$TimeoutSec = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path ".").Path
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "[PROBE] missing venv python: $py" }

# Fast TCP check first
$tnc = Test-NetConnection $IbHost -Port $Port -WarningAction SilentlyContinue
if (-not $tnc.TcpTestSucceeded) {
  Write-Host "[PROBE] TCP_FAIL host=$IbHost port=$Port" -ForegroundColor Yellow
  exit 2
}

$code = @"
import asyncio
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
from ib_insync import IB
async def t():
    ib=IB()
    try:
        await ib.connectAsync(r'$IbHost', $Port, clientId=$ClientId, timeout=$TimeoutSec)
        ct = await ib.reqCurrentTimeAsync()
        print('CONNECT_OK', True)
        print('CURRENT_TIME_OK', ct)
    finally:
        try: ib.disconnect()
        except: pass
asyncio.run(t())
"@

& $py -u -X dev -c $code
$rc = $LASTEXITCODE

if ($rc -eq 0) {
  Write-Host "[PROBE] API_OK host=$IbHost port=$Port clientId=$ClientId" -ForegroundColor Green
  exit 0
}

Write-Host "[PROBE] API_FAIL rc=$rc host=$IbHost port=$Port clientId=$ClientId" -ForegroundColor Yellow
exit 3

