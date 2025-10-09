param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 4002,           # IB Gateway Paper
  [int]$ClientId = 3021,       # use same id as Master API Client ID
  [int]$WaitSec = 45,
  [switch]$Install
)
$ErrorActionPreference = "Stop"
Write-Host "RUNNER BUILD: ibg-preflight-final-v4"

# UTF-8 console
chcp 65001 > $null
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"
$env:PYTEST_ADDOPTS = ""; $env:IB_INT="0"

if ($Install) {
  python -m pip install --upgrade pip --disable-pip-version-check --no-color | Out-Null
  python -m pip install -U pytest ib_insync --disable-pip-version-check --no-color | Out-Null
}

function Test-PortFast([string]$H,[int]$P,[int]$Ms=800){
  $c = New-Object System.Net.Sockets.TcpClient
  try {
    $iar=$c.BeginConnect($H,$P,$null,$null)
    if(-not $iar.AsyncWaitHandle.WaitOne($Ms,$false)) { "CLOSED" } else { $c.EndConnect($iar); "OPEN" }
  } catch { "CLOSED" } finally { $c.Close() }
}

function Wait-Owner([string]$H,[int]$P,[string]$Expect,[int]$TotalSec){
  $deadline=(Get-Date).AddSeconds($TotalSec)
  while((Get-Date) -lt $deadline){
    if((Test-PortFast $H $P 600) -eq "OPEN"){
      $tcp = Get-NetTCPConnection -State Listen -LocalPort $P -ErrorAction SilentlyContinue | Select-Object -First 1
      if($tcp){
        $ownerName = $null
        try {
          $op = $tcp.OwningProcess
          if ($op -is [int]) {
            $ownerName = (Get-Process -Id $op -ErrorAction Stop).Name
          } elseif ($op -is [System.Diagnostics.Process]) {
            $ownerName = $op.Name
          } else {
            try { $pid = [int]$op; $ownerName = (Get-Process -Id $pid -ErrorAction SilentlyContinue).Name } catch { $ownerName = $null }
          }
        } catch { $ownerName = $null }
        if ($ownerName -and ($ownerName -like $Expect)) { return $true }
      }
    }
    Start-Sleep -Milliseconds 700
  }
  return $false
}

# 1) owner settle
$ownerOk = Wait-Owner -H $HostName -P $Port -Expect "ibgateway" -TotalSec $WaitSec
Write-Host ("Owner check: {0}:{1} ownedByIBG={2}" -f $HostName,$Port,$ownerOk)
Start-Sleep -Seconds 6

# 2) ib_insync preflight: cid=3021 (60s) then cid=0 (45s)
$py = @"
from ib_insync import IB
import sys
def try_cid(cid, host='$HostName', port=$Port, tout=60):
    ib=IB()
    try:
        ok=ib.connect(host, port, clientId=cid, timeout=tout)
        if not ok and hasattr(ib,'isConnected') and not ib.isConnected():
            raise RuntimeError('connect returned False')
        print('preflight OK cid', cid, 'serverTime:', ib.reqCurrentTime())
        ib.disconnect(); return 0
    except Exception as e:
        print('preflight cid', cid, 'EXC', type(e).__name__, e, file=sys.stderr)
        try: ib.disconnect()
        except: pass
        return 2
rc = try_cid($ClientId, tout=60)
if rc != 0:
    rc = try_cid(0, tout=45)
sys.exit(rc)
"@
$tmp = Join-Path $env:TEMP ("ibg_pf_{0}.py" -f ([Guid]::NewGuid()))
[System.IO.File]::WriteAllText($tmp,$py,[System.Text.UTF8Encoding]::new($false))
$p = Start-Process -FilePath (Get-Command python).Source -ArgumentList $tmp -NoNewWindow -PassThru -Wait `
  -RedirectStandardOutput ($tmp+'.out') -RedirectStandardError ($tmp+'.err')
Get-Content ($tmp+'.out') | Write-Host
Get-Content ($tmp+'.err') | ForEach-Object { Write-Host $_ -ForegroundColor Yellow } | Out-Null
$ok = ($p.ExitCode -eq 0)
Remove-Item $tmp,($tmp+'.out'),($tmp+'.err') -ErrorAction SilentlyContinue

# 3) export envs; on fail, print log hint and skip
$env:IB_HOST=$HostName; $env:IB_PORT="$Port"; $env:IB_CLIENT_ID="$ClientId"
if($ok){ $env:IB_INT="1"; Start-Sleep -Seconds 2 }
else{
  $env:IB_INT="0"; Write-Host "IB preflight failed → tests will skip." -ForegroundColor Yellow
  $lg = Get-ChildItem "C:\Jts\ibgateway\*\logs\*.log" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Desc | Select-Object -First 1
  if($lg){
    Write-Host ("Log: {0}" -f $lg.FullName) -ForegroundColor Cyan
    Select-String -Path $lg.FullName -Pattern "API","socket","clientId","approval","reject","denied","localhost","trusted","read-only" -SimpleMatch |
      Select-Object -Last 30 | ForEach-Object{ $_.ToString() }
  }
}

# 4) run the single integration file (gated)
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH = (Join-Path (Resolve-Path ".") "src")
$testFile = (Resolve-Path "tests\integration\test_ib_paper_smoke.py").Path

$tmpDir = Join-Path $env:TEMP ("pytest_ibg_int_{0}" -f ([Guid]::NewGuid()))
New-Item -ItemType Directory -Path $tmpDir | Out-Null
$tmpIni = Join-Path $tmpDir "pytest.ini"
[System.IO.File]::WriteAllText($tmpIni, "[pytest]`naddopts = -q --maxfail=1`nfilterwarnings =`n    ignore::Warning`ntestpaths = .`n", [System.Text.UTF8Encoding]::new($false))

Push-Location $tmpDir
try {
  python -m pytest -c $tmpIni --rootdir $tmpDir --confcutdir $tmpDir -p no:pytest_cov "$testFile"
} finally {
  Pop-Location
  Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
}
