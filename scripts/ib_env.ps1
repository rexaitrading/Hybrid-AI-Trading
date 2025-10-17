function Use-IBPaper {
  Set-Item Env:IB_HOST '127.0.0.1'
  Set-Item Env:IB_PORT '4002'
  Set-Item Env:IB_CLIENT_ID '3001'
  Set-Item Env:HAT_MARKET_DATA '3'  # delayed
  Write-Host ("Paper  -> {0}:{1} (clientId={2}, MDT={3})" -f $env:IB_HOST,$env:IB_PORT,$env:IB_CLIENT_ID,$env:HAT_MARKET_DATA)
}
function Use-IBLive {
  Set-Item Env:IB_HOST '127.0.0.1'
  Set-Item Env:IB_PORT '4001'
  Set-Item Env:IB_CLIENT_ID '5003'
  Set-Item Env:HAT_MARKET_DATA '1'  # live
  Write-Host ("Live   -> {0}:{1} (clientId={2}, MDT={3})" -f $env:IB_HOST,$env:IB_PORT,$env:IB_CLIENT_ID,$env:HAT_MARKET_DATA)
}
function Use-ReadOnly { Set-Item Env:HAT_READONLY '1'; Write-Host "Read-Only ON" }
function Use-Writeable { Remove-Item Env:HAT_READONLY -ErrorAction SilentlyContinue; Write-Host "Read-Only OFF" }
function Use-DelayedQuotes { Set-Item Env:HAT_MARKET_DATA '3'; Write-Host "MarketDataType=DELAYED (3)" }
function Use-LiveQuotes    { Set-Item Env:HAT_MARKET_DATA '1'; Write-Host "MarketDataType=LIVE (1)" }

function Probe-IB {
  Write-Host ("Probing {0}:{1} (clientId={2})..." -f $env:IB_HOST,$env:IB_PORT,$env:IB_CLIENT_ID)
  .\.venv\Scripts\python.exe -c "from ib_insync import *; ib=IB();
ok=ib.connect('$env:IB_HOST', int('$env:IB_PORT'), clientId=int('$env:IB_CLIENT_ID'), timeout=30);
print('OK', bool(ok), 'sv', ib.client.serverVersion()); print('time', ib.reqCurrentTime() if ok else None); ib.disconnect()"
}

# Unfiltered runner (as before)
function RunStream {
  param([string]$IHost=$env:IB_HOST,[int]$IPort=[int]$env:IB_PORT,[int]$IClient=[int]$env:IB_CLIENT_ID)
  Write-Host ("Starting runner_stream.py  {0}:{1} (clientId={2}, MDT={3})" -f $IHost,$IPort,$IClient,$env:HAT_MARKET_DATA)
  .\.venv\Scripts\python.exe -u .\src\hybrid_ai_trading\runners\runner_stream.py --host $IHost --port $IPort --client-id $IClient
}

# 2) Tiny error-filter *without touching Python* (PowerShell pipeline)
#    Hides HMDS 2107 chatter and Read-Only lines.
function RunStreamFiltered {
  param([string]$IHost=$env:IB_HOST,[int]$IPort=[int]$env:IB_PORT,[int]$IClient=[int]$env:IB_CLIENT_ID)
  Write-Host ("Starting (filtered) runner_stream.py {0}:{1} (clientId={2}, MDT={3})" -f $IHost,$IPort,$IClient,$env:HAT_MARKET_DATA)
  $cmd = ".\.venv\Scripts\python.exe -u .\src\hybrid_ai_trading\runners\runner_stream.py --host $IHost --port $IPort --client-id $IClient"
  # Pipe both stdout+stderr through a filter that drops 2107 HMDS and Read-Only messages
  cmd /c $cmd 2>&1 | Where-Object { $_ -notmatch 'HMDS data farm|Read-Only' }
}

function Run-StreamPaper { Use-IBPaper; Probe-IB; RunStream }
function Run-StreamLive  { Use-IBLive ; Probe-IB; RunStream }
function Run-StreamPaperFiltered { Use-IBPaper; Probe-IB; RunStreamFiltered }
function Run-StreamLiveFiltered  { Use-IBLive ; Probe-IB; RunStreamFiltered }