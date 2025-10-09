param(
  [int]$ClientId = 3021,
  [int]$TimeoutSec = 45
)

$ErrorActionPreference = "Stop"
$ts     = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir = Join-Path (Resolve-Path ".") "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "ibg_handshake_${ts}.log"
function Log($m){("{0} {1}" -f (Get-Date -Format "HH:mm:ss"),$m) | Tee-Object -FilePath $logFile -Append}

Log "=== IBG Handshake start (port=4003, clientId=$ClientId, timeout=$TimeoutSec) ==="

# kill stale python clients
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 300

# wait up to 60s for 4003 to listen
$open = $false
for ($i=1; $i -le 20; $i++){
  if ((Test-NetConnection 127.0.0.1 -Port 4003 -WarningAction SilentlyContinue).TcpTestSucceeded){ $open=$true; break }
  if ($i -eq 1){ Log "[PORT] Waiting for 127.0.0.1:4003 ..." }
  Start-Sleep -Seconds 3
}
if (-not $open){ Log "[PORT] FATAL: 4003 not listening. Ensure IB Gateway (Paper) is logged in, API enabled, port=4003."; exit 2 }
Log "[PORT] Listening on 127.0.0.1:4003 ✅"

# env for python probe
$env:IB_HOST="127.0.0.1"
$env:IB_PORT="4003"
$env:IB_CLIENT_ID="$ClientId"
$env:IB_TIMEOUT="$TimeoutSec"

# python handshake: retries, then fallback to clientId=0 (no infinite loops)
$py = @"
from ib_insync import *
import os, time, sys
host=os.environ.get("IB_HOST","127.0.0.1")
port=int(os.environ.get("IB_PORT","4003"))
cid =int(os.environ.get("IB_CLIENT_ID","3021"))
tout=float(os.environ.get("IB_TIMEOUT","45"))
ib=IB()

def attempt(client_id, tries=3, delay=4):
    for i in range(1, tries+1):
        try:
            print(f"[connect] {i}/{tries} -> {host}:{port} cid={client_id} tout={tout}")
            ok = ib.connect(host, port, clientId=client_id, timeout=tout)
            if ok:
                ib.waitOnUpdate(timeout=tout)  # server hello / nextValidId
                print("OK:", bool(ok), "serverTime:", ib.serverTime())
                return True
        except Exception as e:
            print("error:", type(e).__name__, str(e))
        time.sleep(delay)
    return False

if not attempt(cid):
    print("[fallback] trying clientId=0 once...")
    if not attempt(0):
        print("HANDSHAKE_FAIL"); sys.exit(2)

a = ib.reqAccountSummary()
print("accountSummary items:", len(a))
ib.disconnect(); print("HANDSHAKE_OK")
"@

Log "[PROBE] Running Python handshake..."
$pyOut = $py | python - 2>&1
$code  = $LASTEXITCODE
$pyOut | Tee-Object -FilePath $logFile -Append | Out-Null
Log "[PROBE] ExitCode: $code"

if ($code -ne 0){
  Log "[DIAG] Handshake failed. Showing latest Gateway API lines:"
  $gwLog = Get-ChildItem "C:\Jts\ibgateway\*\logs\*.log" -ErrorAction SilentlyContinue |
           Sort-Object LastWriteTime -desc | Select-Object -First 1
  if ($gwLog){
    Log ("-- " + $gwLog.FullName + " --")
    Select-String -Path $gwLog.FullName -Pattern "API","socket","Socket","clientId","127.0.0.1","connect" -SimpleMatch |
      Select-Object -Last 50 | ForEach-Object { $_.ToString() | Tee-Object -FilePath $logFile -Append | Out-Null }
  } else {
    Log "[DIAG] No gateway logs found."
  }
  Log "Tips: Gateway→API Settings (PAPER): Enable ActiveX+Socket ON, Read-Only OFF, Port=4003, Allow localhost ON,"
  Log "      Trusted IP=127.0.0.1, Master API Client ID = 0 or your clientId; approve incoming API prompt."
  exit $code
}

Log "✅ HANDSHAKE PASSED. See $logFile"
exit 0