# BUILD: v2-preflight-gated (IB_INT defaults to 0; set to 1 ONLY on successful handshake)
param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 4002,            # IB Gateway Paper
  [int]$ClientId = 9021,        # distinct from daily 3021
  [int]$WaitSec = 90,           # total wait for ready
  [switch]$Launch,              # call Phase-1 launcher
  [switch]$Install,             # pip install pytest/ib_insync
  [switch]$TwsFallback,         # try TWS Paper (7497) if IBG not ready
  [int]$TwsClientId = 9721
)
$ErrorActionPreference = "Stop"

# ---- UTF-8 console ----
chcp 65001 > $null
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING = "utf-8"; $env:PYTHONUTF8 = "1"
$env:PYTEST_ADDOPTS = ""
$env:IB_INT = "0"   # DEFAULT to skip; enable ONLY after preflight OK
Write-Host "RUNNER BUILD: v2-preflight-gated"

if ($Install) {
  python -m pip install --upgrade pip --disable-pip-version-check --no-color | Out-Null
  python -m pip install -U pytest ib_insync --disable-pip-version-check --no-color | Out-Null
}

if ($Launch) {
  $phase1 = Join-Path (Resolve-Path ".") "scripts\phase1_ib_connect.ps1"
  if (Test-Path $phase1) {
    powershell -ExecutionPolicy Bypass -File $phase1 -Profile PAPER -ClientId $ClientId -Launch | Write-Host
  }
}

function Test-PortFast([string]$H,[int]$P,[int]$Ms=800){
  $c = New-Object System.Net.Sockets.TcpClient
  try{
    $iar=$c.BeginConnect($H,$P,$null,$null)
    if(-not $iar.AsyncWaitHandle.WaitOne($Ms,$false)){"CLOSED"} else { $c.EndConnect($iar); "OPEN" }
  }catch{"CLOSED"}finally{$c.Close()}
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
            $ownerName = (Get-Process -Id ([int]$op) -ErrorAction SilentlyContinue).Name
          }
        } catch { $ownerName = $null }
        if ($ownerName -and ($ownerName -like $Expect)) { return $true }
      }
    }
    Start-Sleep -Milliseconds 700
  }
  return $false
}}
    }
    Start-Sleep -Milliseconds 700
  }
  return $false
}

# Prefer IBG Paper; optionally fallback to TWS Paper
$ownerOk = Wait-Owner -H $HostName -P $Port -Expect "ibgateway" -TotalSec $WaitSec
if (-not $ownerOk -and $TwsFallback) {
  Write-Host ("WARN: {0}:{1} not owned by ibgateway.exe; trying TWS Paper 127.0.0.1:7497" -f $HostName,$Port) -ForegroundColor Yellow
  $HostName = "127.0.0.1"; $Port = 7497; $ClientId = $TwsClientId
  $ownerOk = Wait-Owner -H $HostName -P $Port -Expect "tws*" -TotalSec $WaitSec
}

# ---- Robust preflight: 3 attempts (connect + reqCurrentTime) ----
$pyProbe = @"
from ib_insync import IB
import sys, time
host='$HostName'; port=$Port; cid=$ClientId
ib=IB()
for i in range(1,4):
    try:
        ok=ib.connect(host, port, clientId=cid, timeout=30)
        if not ok and hasattr(ib,'isConnected') and not ib.isConnected():
            raise RuntimeError('connect returned False')
        t=ib.reqCurrentTime()
        print('preflight OK attempt', i, 'serverTime:', t)
        ib.disconnect(); sys.exit(0)
    except Exception as e:
        print('preflight attempt', i, 'failed:', type(e).__name__, e, file=sys.stderr)
        try: ib.disconnect()
        except: pass
        time.sleep(3)
sys.exit(2)
"@
$tmpProbe = Join-Path $env:TEMP ("ibg_preflight_{0}.py" -f ([Guid]::NewGuid()))
[System.IO.File]::WriteAllText($tmpProbe, $pyProbe, [System.Text.UTF8Encoding]::new($false))
$stdout = Join-Path $env:TEMP ("ibg_preflight_{0}.out.txt" -f ([Guid]::NewGuid()))
$stderr = Join-Path $env:TEMP ("ibg_preflight_{0}.err.txt" -f ([Guid]::NewGuid()))
$proc = Start-Process -FilePath (Get-Command python).Source -ArgumentList $tmpProbe `
  -NoNewWindow -PassThru -Wait -RedirectStandardOutput $stdout -RedirectStandardError $stderr
$preflightOk = ($proc.ExitCode -eq 0)
Get-Content $stdout | Write-Host
Get-Content $stderr | ForEach-Object { Write-Host $_ -ForegroundColor Yellow } | Out-Null
Remove-Item $tmpProbe,$stdout,$stderr -ErrorAction SilentlyContinue

# ---- Export envs ONLY after preflight OK ----
$env:IB_HOST=$HostName; $env:IB_PORT="$Port"; $env:IB_CLIENT_ID="$ClientId"
if($preflightOk){ $env:IB_INT="1"; Start-Sleep -Seconds 2 } else { $env:IB_INT="0"; Write-Host "IB preflight failed ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ IB_INT=0; integration tests will skip." -ForegroundColor Yellow }

# ---- Run the single integration file (disable plugin autoload & silence warnings) ----
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
$env:PYTHONPATH = (Join-Path (Resolve-Path ".") "src")
$testFile = (Resolve-Path "tests\integration\test_ib_paper_smoke.py").Path

# Minimal temp pytest.ini (UTF-8 no BOM) + filterwarnings
$tmpDir = Join-Path $env:TEMP ("pytest_ibint_{0}" -f ([Guid]::NewGuid()))
New-Item -ItemType Directory -Path $tmpDir | Out-Null
$tmpIni = Join-Path $tmpDir "pytest.ini"
$iniText = "[pytest]`naddopts = -q --maxfail=1`nfilterwarnings =`n    ignore::Warning`ntestpaths = .`n"
[System.IO.File]::WriteAllText($tmpIni, $iniText, [System.Text.UTF8Encoding]::new($false))

Push-Location $tmpDir
try {
  python -m pytest -c $tmpIni --rootdir $tmpDir --confcutdir $tmpDir -p no:pytest_cov "$testFile"
} finally {
  Pop-Location
  Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
}
