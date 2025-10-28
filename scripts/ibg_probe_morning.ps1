$ErrorActionPreference = 'Continue'
$Py = ".\.venv\Scripts\python.exe"
$host = $env:IB_HOST; if (-not $host) { $host = 'localhost' }
$port = $env:IB_PORT; if (-not $port) { $port = '4002' }
$cid  = $env:IB_CLIENT_ID; if (-not $cid) { $cid = '3021' }
$code = "from ib_insync import IB; ib=IB(); ok=ib.connect('$host',int('$port'),clientId=int('$cid'),timeout=20); print('ok',bool(ok)); print('t', ib.reqCurrentTime() if ok else None); ib.disconnect()"
$out  = & $Py -c $code 2>&1
$ts   = Get-Date -Format 'yyyyMMdd_HHmmss'
New-Item -ItemType Directory -Force -Path .\.logs | Out-Null
$log  = ".\.logs\ibg_health.$ts.log"
$out | Out-File -FilePath $log -Encoding UTF8
Write-Host "Health probe wrote: $log"
