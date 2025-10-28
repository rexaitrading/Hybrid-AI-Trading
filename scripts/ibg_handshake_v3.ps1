param(
  [int]$Port       = 4002,   # Paper default
  [int]$ClientId   = 3021,
  [int]$TimeoutSec = 45
)

$ErrorActionPreference = "Stop"
$ts     = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir = Join-Path (Resolve-Path ".") "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log    = Join-Path $logDir "ibg_handshake_v3_${ts}.log"
function Log($m){("{0} {1}" -f (Get-Date -Format "HH:mm:ss"), $m) | Tee-Object -FilePath $log -Append}

# --- helpers
function Test-PortFast {
  param([string]$HostName="127.0.0.1",[int]$Port=4002,[int]$MsTimeout=800)
  $c = New-Object System.Net.Sockets.TcpClient
  try {
    $iar = $c.BeginConnect($HostName,$Port,$null,$null)
    if (-not $iar.AsyncWaitHandle.WaitOne($MsTimeout,$false)) { "CLOSED"; return }
    $c.EndConnect($iar); "OPEN"
  } catch { "CLOSED" } finally { $c.Close() }
}

function Wait-For-IBG([int]$Port,[int]$Seconds=120){
  $ok = $false
  1..$Seconds | ForEach-Object {
    Start-Sleep -Seconds 1
    if ((Test-PortFast 127.0.0.1 $Port 500) -eq "OPEN") {
      $tcp = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
      if ($tcp) {
        $proc = Get-Process -Id $tcp.OwningProcess -ErrorAction SilentlyContinue
        if ($proc -and $proc.Name -eq 'ibgateway') { $ok = $true; break }
      }
    }
    if ($_ % 10 -eq 0) { Log ("...waiting for port {0} owned by ibgateway (sec {1})" -f $Port, $_) }
  }
  if (-not $ok) { throw "Port $Port not owned by ibgateway yet. Finish login + API settings, then rerun." }
}

function Run-Probe([int]$Port,[int]$ClientId,[int]$TimeoutSec,[string]$Tag){
  $pyPath = (Get-Command python).Source
  if (-not $pyPath) { throw "python not found in PATH/venv" }

  $tmpPy  = Join-Path $env:TEMP "ibg_probe_${Tag}_${ts}.py"
  $out    = Join-Path $logDir   "ibg_probe_${Tag}_${ts}.out.txt"
  $err    = Join-Path $logDir   "ibg_probe_${Tag}_${ts}.err.txt"

  $py = @"
from ib_insync import *
import os, sys, time
host='127.0.0.1'; port=$Port; cid=$ClientId; tout=$TimeoutSec
ib=IB()
try:
    print(f"[probe-$Tag] connecting {host}:{port} cid={cid} tout={tout}")
    ok=ib.connect(host,port,clientId=cid,timeout=tout)
    print(f"[probe-$Tag] ok={ok}")
    if ok:
        ib.waitOnUpdate(timeout=tout)
        print("[probe-$Tag] serverTime:", ib.serverTime())
        print("[probe-$Tag] acctSummary:", len(ib.reqAccountSummary()))
        ib.disconnect()
        sys.exit(0)
    else:
        sys.exit(2)
except Exception as e:
    print("[probe-$Tag] EXC:", type(e).__name__, str(e), file=sys.stderr)
    try:
        ib.disconnect()
    except Exception:
        pass
    sys.exit(2)
"@
  [System.IO.File]::WriteAllText($tmpPy, $py, (New-Object System.Text.UTF8Encoding($false)))

  $p = Start-Process -FilePath $pyPath -ArgumentList $tmpPy `
        -RedirectStandardOutput $out -RedirectStandardError $err `
        -NoNewWindow -PassThru
  if (-not (Wait-Process -Id $p.Id -Timeout ($TimeoutSec + 10) -ErrorAction SilentlyContinue)) {
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    Add-Content $err "[probe-$Tag] TIMEOUT after $(($TimeoutSec + 10))s"
    return 124
  }
  Get-Content $out | Tee-Object -FilePath $log -Append | Out-Null
  Get-Content $err | Tee-Object -FilePath $log -Append | Out-Null
  return $p.ExitCode
}

# --- main
Log "=== v3 start (port=$Port, cid=$ClientId, tout=$TimeoutSec) ==="
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 200

Wait-For-IBG -Port $Port -Seconds 120
Log "[PORT] $Port is OPEN and owned by ibgateway.exe âœ…"

# 1) try requested clientId
$rc = Run-Probe -Port $Port -ClientId $ClientId -TimeoutSec $TimeoutSec -Tag "cid$ClientId"
Log "[PROBE cid=$ClientId] exit=$rc"

if ($rc -ne 0) {
  # 2) single fallback to cid=0
  $rc2 = Run-Probe -Port $Port -ClientId 0 -TimeoutSec $TimeoutSec -Tag "cid0"
  Log "[PROBE cid=0] exit=$rc2"

  if ($rc2 -ne 0) {
    Log "[DIAG] Python probe failed. Tail of latest IBG log:"
    $gw = Get-ChildItem "C:\Jts\ibgateway\*\logs\*.log" -ErrorAction SilentlyContinue |
          Sort-Object LastWriteTime -desc | Select-Object -First 1
    if ($gw) {
      Log ("-- " + $gw.FullName + " --")
      Select-String -Path $gw.FullName -Pattern "API","socket","Socket","clientId","127.0.0.1","connect" -SimpleMatch |
        Select-Object -Last 80 | ForEach-Object { $_.ToString() | Tee-Object -FilePath $log -Append | Out-Null }
    } else {
      Log "[DIAG] No gateway logs found."
    }
    Log "Fix in Gatewayâ†’API (Paper): Enable ActiveX+Socket ON, Read-Only OFF, Port=$Port,"
    Log "  Master API Client ID = 0 (or exactly $ClientId), Allow localhost ON, Trusted IP 127.0.0.1,"
    Log "  approve the first 'Incoming API connection' prompt, then Save & Restart."
    Log "âŒ HANDSHAKE FAILED. See $log"
    exit 2
  }
}

Log "âœ… HANDSHAKE PASSED. See $log"
exit 0
