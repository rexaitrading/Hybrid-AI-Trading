param(
  [int]$ClientId = 3021,
  [int]$TimeoutSec = 45,
  [int]$Port = 4003
)

$ErrorActionPreference = "Stop"
$ts     = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir = Join-Path (Resolve-Path ".") "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "ibg_handshake_${ts}.log"
function Log($m){("{0} {1}" -f (Get-Date -Format "HH:mm:ss"),$m) | Tee-Object -FilePath $logFile -Append}

Log "=== IBG Handshake v2 (port=$Port, clientId=$ClientId, timeout=$TimeoutSec) ==="

# 1) Kill stale python clients
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 300

# 2) Wait up to 60s for the port to listen
$open = $false
for ($i=1; $i -le 20; $i++){
  if ((Test-NetConnection 127.0.0.1 -Port $Port -WarningAction SilentlyContinue).TcpTestSucceeded){ $open=$true; break }
  if ($i -eq 1){ Log "[PORT] Waiting for 127.0.0.1:$Port ..." }
  Start-Sleep -Seconds 3
}
if (-not $open){ Log "[PORT] FATAL: $Port not listening. Ensure IB Gateway (Paper) is logged in, API enabled, port=$Port."; exit 2 }
Log "[PORT] Listening on 127.0.0.1:$Port ✅"

# 3) Env for probe
$env:IB_HOST="127.0.0.1"
$env:IB_PORT="$Port"
$env:IB_CLIENT_ID="$ClientId"
$env:IB_TIMEOUT="$TimeoutSec"

# 4) Write a temp python probe (tries cid, then cid=0; no infinite loop)
$probe = Join-Path $env:TEMP "ibg_probe_${ts}.py"
$py = @"
from ib_insync import *
import os, time, sys
host=os.getenv('IB_HOST','127.0.0.1'); port=int(os.getenv('IB_PORT','4003'))
cid=int(os.getenv('IB_CLIENT_ID','3021')); tout=float(os.getenv('IB_TIMEOUT','45'))
ib=IB()

def attempt(client_id, tries=3, delay=4):
    for i in range(1,tries+1):
        try:
            print(f"[connect] {i}/{tries} -> {host}:{port} cid={client_id} tout={tout}")
            ok = ib.connect(host, port, clientId=client_id, timeout=tout)
            if ok:
                ib.waitOnUpdate(timeout=tout)
                print("OK:", bool(ok), "serverTime:", ib.serverTime())
                return True
        except Exception as e:
            print("error:", type(e).__name__, str(e), file=sys.stderr)
        time.sleep(delay)
    return False

if not attempt(cid):
    print("[fallback] trying clientId=0 once...")
    if not attempt(0):
        sys.exit(2)

a = ib.reqAccountSummary()
print("accountSummary items:", len(a))
ib.disconnect()
sys.exit(0)
"@
[System.IO.File]::WriteAllText($probe, $py, (New-Object System.Text.UTF8Encoding($false)))

# 5) Run python via Start-Process with redirected output (prevents NativeCommandError)
$outFile = Join-Path $logDir "ibg_probe_${ts}.out.txt"
$errFile = Join-Path $logDir "ibg_probe_${ts}.err.txt"
$python = (Get-Command python).Source
if (-not $python) { Log "[PROBE] python not found in PATH"; exit 3 }

$proc = Start-Process -FilePath $python -ArgumentList $probe -NoNewWindow -PassThru -Wait `
  -RedirectStandardOutput $outFile -RedirectStandardError $errFile
$code = $proc.ExitCode

Get-Content $outFile | Tee-Object -FilePath $logFile -Append | Out-Null
Get-Content $errFile | Tee-Object -FilePath $logFile -Append | Out-Null
Log "[PROBE] ExitCode: $code"

if ($code -ne 0){
  Log "[DIAG] Python probe failed. Surfacing latest Gateway API lines:"
  $gwLog = Get-ChildItem "C:\Jts\ibgateway\*\logs\*.log" -ErrorAction SilentlyContinue |
           Sort-Object LastWriteTime -desc | Select-Object -First 1
  if ($gwLog){
    Log ("-- " + $gwLog.FullName + " --")
    Select-String -Path $gwLog.FullName -Pattern "API","socket","Socket","clientId","127.0.0.1","connect" -SimpleMatch |
      Select-Object -Last 80 | ForEach-Object { $_.ToString() | Tee-Object -FilePath $logFile -Append | Out-Null }
  } else {
    Log "[DIAG] No gateway logs found."
  }
  Log "Fix on Gateway→API (Paper): Enable ActiveX+Socket ON, Read-Only OFF, Port=$Port,"
  Log "  Master API Client ID = 0 (or exactly $ClientId), Allow localhost ON, Trusted IP 127.0.0.1,"
  Log "  approve the first 'Incoming API connection' prompt, then restart Gateway."
  exit $code
}

Log "✅ HANDSHAKE PASSED. See $logFile"
exit 0
