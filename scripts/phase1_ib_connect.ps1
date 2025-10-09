param(
  [ValidateSet("PAPER","LIVE")] [string]$Profile = "PAPER",
  [int]$ClientId = 3021,
  [switch]$Launch,
  [switch]$EnsureFirewall
)

$ErrorActionPreference = "Stop"
$Port = if ($Profile -eq "PAPER") { 4002 } else { 4001 }
$ts   = Get-Date -Format "yyyyMMdd_HHmmss"
$logD = Join-Path (Resolve-Path ".") "logs"
New-Item -ItemType Directory -Force -Path $logD | Out-Null
$log  = Join-Path $logD ("phase1_{0}_{1}.log" -f $Profile,$ts)
function Log($m){("{0} {1}" -f (Get-Date -Format "HH:mm:ss"), $m) | Tee-Object -FilePath $log -Append}

Log "=== Phase1 start: $Profile port=$Port clientId=$ClientId ==="

# ---------- (optional) firewall ----------
if ($EnsureFirewall) {
  $isAdmin = (New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
             ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  if (-not $isAdmin) {
    Log "[FW] Elevating..."
    $args = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Profile $Profile -ClientId $ClientId -EnsureFirewall"
    Start-Process powershell.exe -Verb RunAs -ArgumentList $args
    exit
  }
  $ibgExe = (Get-ChildItem "C:\Jts\ibgateway\*\ibgateway.exe" -ErrorAction SilentlyContinue |
             Sort-Object LastWriteTime -Desc | Select-Object -First 1).FullName
  if ($ibgExe) {
    if (-not (Get-NetFirewallRule -DisplayName "IB Gateway API (Program)" -ErrorAction SilentlyContinue)) {
      New-NetFirewallRule -DisplayName "IB Gateway API (Program)" -Program $ibgExe -Direction Inbound -Action Allow -Profile Private,Domain | Out-Null
    } else {
      Set-NetFirewallRule -DisplayName "IB Gateway API (Program)" -Enabled True -Action Allow -Profile Private,Domain | Out-Null
    }
    $ruleName = "IB Gateway API Port $Port"
    if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
      New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -Profile Private,Domain | Out-Null
    } else {
      Set-NetFirewallRule -DisplayName $ruleName -Enabled True -Action Allow -Profile Private,Domain | Out-Null
    }
    Log "[FW] Rules ensured."
  } else { Log "[FW] ibgateway.exe not found under C:\Jts\ibgateway" }
}

# ---------- (optional) launch IB Gateway ----------
if ($Launch) {
  $ibgExe = (Get-ChildItem "C:\Jts\ibgateway\*\ibgateway.exe" -ErrorAction SilentlyContinue |
             Sort-Object LastWriteTime -Desc | Select-Object -First 1).FullName
  if ($ibgExe) { Log "[LAUNCH] $ibgExe"; Start-Process -FilePath $ibgExe | Out-Null; Start-Sleep 2 }
  else { Log "[LAUNCH] ibgateway.exe not found." }
}

# ---------- wait for port open & correct owner ----------
function Test-PortFast {
  param([string]$HostName="127.0.0.1",[int]$Port=4002,[int]$MsTimeout=800)
  $c = New-Object System.Net.Sockets.TcpClient
  try{
    $iar = $c.BeginConnect($HostName,$Port,$null,$null)
    if(-not $iar.AsyncWaitHandle.WaitOne($MsTimeout,$false)){ "CLOSED"; return }
    $c.EndConnect($iar); "OPEN"
  }catch{"CLOSED"}finally{$c.Close()}
}

$ok = $false
1..120 | ForEach-Object {
  Start-Sleep -Seconds 1
  if ((Test-PortFast -HostName 127.0.0.1 -Port $Port -MsTimeout 600) -eq "OPEN") {
    $tcp = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($tcp) {
      $p = Get-Process -Id $tcp.OwningProcess -ErrorAction SilentlyContinue
      if ($p -and $p.Name -eq 'ibgateway') { $ok = $true; break }
    }
  }
  if ($_ % 10 -eq 0) { Log ("...waiting for {0} owned by ibgateway (sec {1})" -f $Port, $_) }
}
if (-not $ok) { Log "FATAL: Port $Port not owned by ibgateway.exe. Login + API settings ($Profile), then re-run."; exit 2 }
Log "[PORT] $Port is OPEN and owned by ibgateway.exe ✅"

# ---------- python probe (version-proof) ----------
$stdout = Join-Path $logD ("phase1_py_{0}_{1}.out.txt" -f $Profile,$ts)
$stderr = Join-Path $logD ("phase1_py_{0}_{1}.err.txt" -f $Profile,$ts)
$py = @"
from ib_insync import *
import time, sys
host='127.0.0.1'; port=$Port; cid=$ClientId; tout=45
ib=IB()
try:
    print('[connect]', host, port, 'cid', cid, 'tout', tout)
    ok=ib.connect(host, port, clientId=cid, timeout=tout)
    print('ok:', ok)
    if not ok: sys.exit(2)
    ib.waitOnUpdate(timeout=10)
    print('serverTime:', ib.reqCurrentTime())
    acct=(ib.managedAccounts() or [''])[0]; print('account:', acct)

    ib.client.reqAccountUpdates(True, acct)
    t0=time.time()
    while time.time()-t0 < 3:
        ib.waitOnUpdate(timeout=1.0)
    vals = ib.accountValues() or []
    ib.client.reqAccountUpdates(False, acct)

    want={'NetLiquidation','TotalCashValue','BuyingPower','AvailableFunds'}
    snap=[(v.tag,v.value,v.currency) for v in vals if v.tag in want]
    print('summary:', snap)
    print('openTrades:', [(t.order.orderId,t.orderStatus.status) for t in ib.openTrades()])
    ib.disconnect(); sys.exit(0)
except Exception as e:
    print('EXC:', type(e).__name__, str(e), file=sys.stderr)
    try: ib.disconnect()
    except: pass
    sys.exit(2)
"@

$probe = Join-Path $env:TEMP ("phase1_probe_{0}.py" -f $ts)
[System.IO.File]::WriteAllText($probe, $py, (New-Object System.Text.UTF8Encoding($false)))
$python = (Get-Command python).Source
$proc = Start-Process -FilePath $python -ArgumentList $probe -NoNewWindow -PassThru -Wait `
  -RedirectStandardOutput $stdout -RedirectStandardError $stderr
$code = $proc.ExitCode
Get-Content $stdout | Tee-Object -FilePath $log -Append | Out-Null
Get-Content $stderr | Tee-Object -FilePath $log -Append | Out-Null
Log "[PY] ExitCode=$code"
if ($code -ne 0) { Log "❌ Probe failed. Fix API on $Profile (Read-Only OFF, Master=0/ClientId, localhost ON, Trusted 127.0.0.1). Log: $log"; exit $code }
Log "✅ Phase1 OK. Log: $log"