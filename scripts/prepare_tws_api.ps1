cd "$PSScriptRoot\.."
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "src"

# Honor env; default to 7498
if (-not $env:IB_HOST) { $env:IB_HOST = "127.0.0.1" }
if (-not $env:IB_PORT) { $env:IB_PORT = "7498" }
if (-not $env:IB_CLIENT_ID) { $env:IB_CLIENT_ID = "300" }

# NOTE: do NOT use $host (reserved). Use $ibHost/$ibPort.
$ibHost = $env:IB_HOST
$ibPort = [int]$env:IB_PORT
Write-Host ("`>>> Probing TWS API on {0}:{1} ..." -f $ibHost, $ibPort) -ForegroundColor Cyan

function Test-Port($p){
  try { (Test-NetConnection 127.0.0.1 -Port $p -WarningAction SilentlyContinue).TcpTestSucceeded }
  catch { $false }
}

# brief wait for port to listen
$wait=0
while (-not (Test-Port $ibPort) -and $wait -lt 20) { Start-Sleep -Milliseconds 500; $wait++ }

for ($i=0; $i -lt 20; $i++) {
  python .\scripts\probe_ib_api.py
  if ($LASTEXITCODE -eq 0) { Write-Host ">>> API OK" -ForegroundColor Green; exit 0 }
  [console]::beep(1200,300)
  Start-Sleep -Seconds 2
}
Write-Host ">>> API still not ready (timeout). Check TWS API settings and try again." -ForegroundColor Red
exit 1
