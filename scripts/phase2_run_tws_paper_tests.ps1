# scripts\phase2_run_tws_paper_tests.ps1
# BUILD: tws-paper-preflight-gated
param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 7497,            # TWS Paper
  [int]$ClientId = 9721,        # distinct from your daily 3021
  [int]$WaitSec =  120,
  [switch]$Install
)
$ErrorActionPreference = "Stop"
Write-Host "RUNNER BUILD: tws-paper-preflight-gated"

# UTF-8 console
chcp 65001 > $null
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; $env:PYTEST_ADDOPTS=""; $env:IB_INT="0"

if ($Install) {
  python -m pip install --upgrade pip --disable-pip-version-check --no-color | Out-Null
  python -m pip install -U pytest ib_insync --disable-pip-version-check --no-color | Out-Null
}

function Test-PortFast([string]$H,[int]$P,[int]$Ms=800){
  $c = New-Object System.Net.Sockets.TcpClient
  try{
    $iar=$c.BeginConnect($H,$P,$null,$null)
    if(-not $iar.AsyncWaitHandle.WaitOne($Ms,$false)){"CLOSED"} else { $c.EndConnect($iar); "OPEN" }
  }catch{"CLOSED"}finally{$c.Close()}
}

# Wait up to WaitSec for TWS to be listening and owned by tws.exe
$deadline=(Get-Date).AddSeconds($WaitSec)
while((Get-Date) -lt $deadline){
  if((Test-PortFast $HostName $Port 600) -eq "OPEN"){
    $tcp = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if($tcp){
      try{ $owner=(Get-Process -Id $tcp.OwningProcess -ErrorAction Stop).Name }catch{ $owner=$null }
      if($owner -and ($owner -like "tws*")){ break }
    }
  }
  Start-Sleep -Milliseconds 700
}

# Preflight (3 attempts): connect + reqCurrentTime
$py = @"
from ib_insync import IB
import sys, time
host='$HostName'; port=$Port; cid=$ClientId
ib=IB()
for i in range(1,6):
    try:
        ok=ib.connect(host, port, clientId=cid, timeout=45)
        if not ok and hasattr(ib,'isConnected') and not ib.isConnected():
            raise RuntimeError('connect returned False')
        print('preflight OK attempt', i, 'serverTime:', ib.reqCurrentTime())
        ib.disconnect(); sys.exit(0)
    except Exception as e:
        print('preflight attempt', i, 'failed:', type(e).__name__, e, file=sys.stderr)
        try: ib.disconnect()
        except: pass
        time.sleep(3)
sys.exit(2)
"@
$tmp = Join-Path $env:TEMP ("tws_preflight_{0}.py" -f ([Guid]::NewGuid()))
[IO.File]::WriteAllText($tmp,$py,[Text.UTF8Encoding]::new($false))
$so = Join-Path $env:TEMP ("tws_preflight_{0}.out.txt" -f ([Guid]::NewGuid()))
$se = Join-Path $env:TEMP ("tws_preflight_{0}.err.txt" -f ([Guid]::NewGuid()))
$p  = Start-Process -FilePath (Get-Command python).Source -ArgumentList $tmp -NoNewWindow -PassThru -Wait -RedirectStandardOutput $so -RedirectStandardError $se
$ok = ($p.ExitCode -eq 0)
Get-Content $so | Write-Host
Get-Content $se | ForEach-Object { Write-Host $_ -ForegroundColor Yellow } | Out-Null
Remove-Item $tmp,$so,$se -ErrorAction SilentlyContinue

# Export envs; enable tests only on success
$env:IB_HOST=$HostName; $env:IB_PORT="$Port"; $env:IB_CLIENT_ID="$ClientId"
if($ok){ $env:IB_INT="1"; Start-Sleep -Seconds 2 } else { $env:IB_INT="0"; Write-Host "TWS preflight failed â†’ IB_INT=0; tests will skip." -ForegroundColor Yellow }

# Minimal pytest.ini (UTF-8 no BOM) + filterwarnings; run single file
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH = (Join-Path (Resolve-Path ".") "src")
$testFile = (Resolve-Path "tests\integration\test_ib_paper_smoke.py").Path
$tmpDir = Join-Path $env:TEMP ("pytest_tws_int_{0}" -f ([Guid]::NewGuid()))
New-Item -ItemType Directory -Path $tmpDir | Out-Null
$tmpIni = Join-Path $tmpDir "pytest.ini"
[IO.File]::WriteAllText($tmpIni, "[pytest]`naddopts = -q --maxfail=1`nfilterwarnings =`n    ignore::Warning`ntestpaths = .`n", [Text.UTF8Encoding]::new($false))

Push-Location $tmpDir
try {
  python -m pytest -c $tmpIni --rootdir $tmpDir --confcutdir $tmpDir -p no:pytest_cov "$testFile"
} finally {
  Pop-Location
  Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
}