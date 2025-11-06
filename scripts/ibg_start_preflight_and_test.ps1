param(
  [string]$Exe     = "C:\Jts\ibgateway\1040\ibgateway.exe",
  [int]  $WaitSec  = 300,   # max wait for login/API (sec)
  [int]  $Tout3021 = 45,    # connect timeout for cid 3021
  [int]  $Tout0    = 30,    # connect timeout for cid 0
  [int]  $ConsecOK = 6      # require N consecutive owner=ibgateway checks
)
$ErrorActionPreference="Stop"

function Test-PortFast([string]$H,[int]$P,[int]$Ms=800){
  $c = New-Object System.Net.Sockets.TcpClient
  try { $iar=$c.BeginConnect($H,$P,$null,$null); if(-not $iar.AsyncWaitHandle.WaitOne($Ms,$false)){"CLOSED"} else { $c.EndConnect($iar); "OPEN" } }
  catch { "CLOSED" } finally { $c.Close() }
}
function Wait-ForIBG([int]$totalSec,[int]$needed){
  $deadline=(Get-Date).AddSeconds($totalSec)
  $okCount=0; $tick=0
  while((Get-Date) -lt $deadline){
    $tick+=1
    $open = ((Test-PortFast "127.0.0.1" 4002 600) -eq "OPEN") -or ((Test-PortFast "::1" 4002 600) -eq "OPEN")
    if($open){
      $tcp = Get-NetTCPConnection -State Listen -LocalPort 4002 -ErrorAction SilentlyContinue | Select-Object -First 1
      if($tcp){
        try { $owner=(Get-Process -Id $tcp.OwningProcess -ErrorAction Stop).Name } catch { $owner=$null }
        if($owner -eq "ibgateway"){ $okCount+=1 } else { $okCount=0 }
      } else { $okCount=0 }
    } else { $okCount=0 }

    if($okCount -ge $needed){ return $true }
    if($tick % 7 -eq 0){ Write-Host ("ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦waiting for login & API (sec ~{0})" -f ($tick*0.7)) -ForegroundColor DarkGray }
    Start-Sleep -Milliseconds 700
  }
  return $false
}

Write-Host "Killing any stale IB/TWS/JavaÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦" -ForegroundColor Cyan
'tws.exe','ibgateway.exe','javaw.exe','java.exe' | % { Get-Process $_ -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue }

Write-Host "Starting IB GatewayÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦" -ForegroundColor Cyan
Start-Process $Exe
Write-Host "Log in to Paper; waiting for API listener (4002) to be stably owned by ibgatewayÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦" -ForegroundColor Yellow

if (-not (Wait-ForIBG -totalSec $WaitSec -needed $ConsecOK)) {
  Write-Host "4002 never became stably owned by ibgateway; finish login/API then re-run." -ForegroundColor Yellow
  exit 0
}

Write-Host "Listener is up and stable. Small settleÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦" -ForegroundColor Green
Start-Sleep -Seconds 6

# re-check just before handshake
$tcp = Get-NetTCPConnection -State Listen -LocalPort 4002 -ErrorAction SilentlyContinue | Select-Object -First 1
if(-not $tcp){ Write-Host "Listener dropped; waiting againÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦" -ForegroundColor Yellow; if (-not (Wait-ForIBG -totalSec 90 -needed $ConsecOK)) { exit 0 } }

# Preflight (127.0.0.1 only): 3021 first (Master=3021), then 0 if needed
Write-Host ("Preflight: trying cid=3021 on 127.0.0.1 (timeout {0}s)..." -f $Tout3021) -ForegroundColor Cyan
$py = @"
from ib_insync import IB
import sys
def try_once(cid, tout):
    ib=IB()
    try:
        ok=ib.connect('127.0.0.1', 4002, clientId=cid, timeout=tout)
        if not ok and hasattr(ib,'isConnected') and not ib.isConnected():
            raise RuntimeError('connect returned False')
        print('preflight OK 127.0.0.1 cid', cid, 'serverTime:', ib.reqCurrentTime())
        ib.disconnect(); return 0
    except Exception:
        try: ib.disconnect()
        except: pass
        return 2
rc = try_once(3021, $Tout3021)
if rc != 0:
    print('Preflight: cid=3021 failed; trying cid=0 (timeout', $Tout0, 's)...')
    rc = try_once(0, $Tout0)
sys.exit(rc)
"@
$tmp = Join-Path $env:TEMP ("ibg_pf_{0}.py" -f ([Guid]::NewGuid()))
[IO.File]::WriteAllText($tmp,$py,[System.Text.UTF8Encoding]::new($false))
$p = Start-Process -FilePath (Get-Command python).Source -ArgumentList $tmp -NoNewWindow -PassThru -Wait `
  -RedirectStandardOutput ($tmp+'.out') -RedirectStandardError ($tmp+'.err')
$out = Get-Content ($tmp+'.out'); $ok = ($p.ExitCode -eq 0)
$out | Write-Host
Remove-Item $tmp,($tmp+'.out'),($tmp+'.err') -ErrorAction SilentlyContinue

if(-not $ok){
  Write-Host "Handshake blocked ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ tests will skip. IBG log hint:" -ForegroundColor Yellow
  $lg = Get-ChildItem "C:\Jts\ibgateway\1040\logs\*.log","C:\Jts\ibgateway\*\logs\*.log" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Desc | Select-Object -First 1
  if($lg){
    Write-Host ("Log: {0}" -f $lg.FullName) -ForegroundColor Cyan
    Select-String -Path $lg.FullName -SimpleMatch -Pattern "API","clientId","approval","reject","denied","localhost","trusted","read-only" |
      Select-Object -Last 30 | % { $_.ToString() }
  } else {
    Write-Host "No IBG logs found (not fully initialized yet)." -ForegroundColor Yellow
  }
  exit 0
}

# Run test immediately (no hand-off window)
$env:IB_INT="1"; $env:IB_HOST="127.0.0.1"; $env:IB_PORT="4002"; $env:IB_CLIENT_ID="3021"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH = (Join-Path (Resolve-Path ".") "src")

$testFile = (Resolve-Path "tests\integration\test_ib_paper_smoke.py").Path
$tmpDir = Join-Path $env:TEMP ("pytest_ibg_int_{0}" -f ([Guid]::NewGuid()))
New-Item -ItemType Directory -Path $tmpDir | Out-Null
$tmpIni  = Join-Path $tmpDir "pytest.ini"
[IO.File]::WriteAllText($tmpIni, "[pytest]`naddopts = -q --maxfail=1`nfilterwarnings =`n    ignore::Warning`ntestpaths = .`n", [System.Text.UTF8Encoding]::new($false))

Push-Location $tmpDir
try {
  # NOTE: plugin name quoted with single quotes to avoid colon parsing; $testFile unquoted as it's already a path
  python -m pytest -c $tmpIni --rootdir $tmpDir --confcutdir $tmpDir -p 'no:pytest_cov' $testFile
}
finally {
  Pop-Location
  Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
}
