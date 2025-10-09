param(
  [string]$Exe = "C:\Jts\ibgateway\1040\ibgateway.exe",
  [int]$WaitSec = 240
)
$ErrorActionPreference="Stop"

function Test-PortFast([string]$H,[int]$P,[int]$Ms=800){
  $c = New-Object System.Net.Sockets.TcpClient
  try { $iar=$c.BeginConnect($H,$P,$null,$null); if(-not $iar.AsyncWaitHandle.WaitOne($Ms,$false)){"CLOSED"} else { $c.EndConnect($iar); "OPEN" } }
  catch { "CLOSED" } finally { $c.Close() }
}

Write-Host "Killing any stale IB/TWS/Java" -ForegroundColor Cyan
'tws.exe','ibgateway.exe','javaw.exe','java.exe' | % { Get-Process $_ -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue }

Write-Host "Starting IB Gateway 10.40" -ForegroundColor Cyan
Start-Process $Exe
Write-Host "Log in to Paper and wait; I will detect when API is ready (4002)..." -ForegroundColor Yellow

# wait for 4002 owned by ibgateway (IPv4 or IPv6)
$deadline=(Get-Date).AddSeconds($WaitSec)
$ready=$false
while((Get-Date) -lt $deadline){
  $open = ((Test-PortFast "127.0.0.1" 4002 600) -eq "OPEN") -or ((Test-PortFast "::1" 4002 600) -eq "OPEN")
  if($open){
    $tcp = Get-NetTCPConnection -State Listen -LocalPort 4002 -ErrorAction SilentlyContinue | Select-Object -First 1
    if($tcp){
      try { $name=(Get-Process -Id $tcp.OwningProcess -ErrorAction Stop).Name } catch { $name=$null }
      if($name -eq "ibgateway"){ $ready=$true; break }
    }
  }
  Start-Sleep -Milliseconds 700
}
if(-not $ready){ Write-Host "4002 never became owned by ibgateway; finish Paper login/API then re-run." -ForegroundColor Yellow; return }

Write-Host "Listener is up. Small settle" -ForegroundColor Green
Start-Sleep -Seconds 6

# Try cid=0 FIRST (works today), then 3021
$py = @"
from ib_insync import IB
import sys
hosts = ['127.0.0.1','::1','localhost']
def try_once(cid, tout):
    ib=IB()
    for h in hosts:
        try:
            ok=ib.connect(h, 4002, clientId=cid, timeout=tout)
            if not ok and hasattr(ib,'isConnected') and not ib.isConnected():
                raise RuntimeError('connect returned False')
            print('preflight OK', h, 'cid', cid, 'serverTime:', ib.reqCurrentTime())
            ib.disconnect(); return 0
        except Exception as e:
            print('preflight', h, 'cid', cid, 'EXC', type(e).__name__, e, file=sys.stderr)
            try: ib.disconnect()
            except: pass
    return 2
rc = try_once(0, 45)
if rc != 0: rc = try_once(3021, 60)
sys.exit(rc)
"@
$tmp = Join-Path $env:TEMP ("ibg_pf_{0}.py" -f ([Guid]::NewGuid()))
[IO.File]::WriteAllText($tmp,$py,[System.Text.UTF8Encoding]::new($false))
$p = Start-Process -FilePath (Get-Command python).Source -ArgumentList $tmp -NoNewWindow -PassThru -Wait `
  -RedirectStandardOutput ($tmp+'.out') -RedirectStandardError ($tmp+'.err')
Get-Content ($tmp+'.out') | Write-Host
Get-Content ($tmp+'.err') | % { if($_){ Write-Host $_ -ForegroundColor Yellow } } | Out-Null
$ok = ($p.ExitCode -eq 0)
Remove-Item $tmp,($tmp+'.out'),($tmp+'.err') -ErrorAction SilentlyContinue

if($ok){
  Write-Host "Handshake passed. Running gated test" -ForegroundColor Green
  powershell -ExecutionPolicy Bypass -File .\scripts\phase2_run_ib_paper_tests_clean.ps1
} else {
  Write-Host "Handshake blocked  tests will skip. Showing IBG log hint:" -ForegroundColor Yellow
  $lg = Get-ChildItem "C:\Jts\ibgateway\1040\logs\*.log","C:\Jts\ibgateway\*\logs\*.log" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Desc | Select-Object -First 1
  if($lg){
    Write-Host ("Log: {0}" -f $lg.FullName) -ForegroundColor Cyan
    Select-String -Path $lg.FullName -Pattern "API","clientId","approval","reject","denied","localhost","trusted","read-only" -SimpleMatch |
      Select-Object -Last 30 | % { $_.ToString() }
  } else {
    Write-Host "No IBG logs found under common paths." -ForegroundColor Yellow
  }
}