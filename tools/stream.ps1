# tools/stream.ps1  clean helpers (PS5.1-safe, SINGLE definition)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Script:ToolsDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$Script:ProjDir  = Split-Path -Path $Script:ToolsDir -Parent
$Script:LogsDir  = Join-Path $Script:ProjDir "logs"
$Script:VenvPy   = Join-Path $Script:ProjDir ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $Script:LogsDir | Out-Null

function stop-stream {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { ($_.CommandLine + "") -match 'runner_stream\.py' } |
    ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }
}

function start-stream {
  [CmdletBinding()]
  param(
    [string]$ClientId = '3021',
    [ValidateSet(1,3)]
    [int]   $MdType   = 3
  )

  if (-not (Test-Path -LiteralPath $Script:VenvPy)) {
    throw "Missing venv python: $Script:VenvPy"
  }

  # Guard: skip if already running (any python)
  $existing = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { ($_.CommandLine + "") -match 'runner_stream\.py' }
  if ($existing) {
    Write-Host "[STREAM] Already running. Skipping new launch." -ForegroundColor Yellow
    return
  }

  # Prefer env IB_PORT else default 4002
  $portStr = $env:IB_PORT
  if ([string]::IsNullOrWhiteSpace($portStr)) { $portStr = "4002" }
  $port = [int]$portStr

  # Fail-closed if IB API port not listening
  $tnc = Test-NetConnection $env:IB_HOST -Port $port -WarningAction SilentlyContinue
  if (-not $tnc.TcpTestSucceeded) {
    throw "IB API port not listening on $env:IB_HOST`:$port"
  }

  # Env for runner
  $env:PYTHONPATH       = (Join-Path $Script:ProjDir 'src')
  $env:PYTHONUNBUFFERED = '1'
  $env:IB_HOST          = '127.0.0.1'
  $env:IB_PORT          = "$port"
  $env:IB_CLIENT_ID     = $ClientId
  $env:IB_MDT           = "$MdType"

  # Log files
  $ts  = Get-Date -Format 'yyyyMMdd_HHmmss'
  $out = Join-Path $Script:LogsDir "stream_run.$ts.out.log"
  $err = Join-Path $Script:LogsDir "stream_run.$ts.err.log"
  '' | Out-File -LiteralPath $out -Encoding utf8
  '' | Out-File -LiteralPath $err -Encoding utf8

  Start-Process -FilePath $Script:VenvPy `
    -WorkingDirectory $Script:ProjDir `
    -ArgumentList @('-u','-X','dev','src\hybrid_ai_trading\runners\runner_stream.py','--client-id',$ClientId) `
    -RedirectStandardOutput $out `
    -RedirectStandardError  $err `
    -WindowStyle Minimized | Out-Null

  Write-Host "Stream booted. OUT: $out"
  Write-Host "Stream booted. ERR: $err"

  # Containment window: for 5 seconds, kill any NON-venv python that appears running runner_stream.py
  try {
    $venv = (Resolve-Path $Script:VenvPy).Path
    for($i=0; $i -lt 10; $i++){
      Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object {
          ($_.CommandLine + "") -match 'runner_stream\.py' -and
          ($_.CommandLine + "") -notmatch [regex]::Escape($venv)
        } |
        ForEach-Object {
          Write-Host ("[STREAM] KILL_NON_VENV pid={0}" -f $_.ProcessId) -ForegroundColor Yellow
          Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
      Start-Sleep -Milliseconds 500
    }
  } catch {}

  return
}

function status-stream {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { ($_.CommandLine + "") -match 'runner_stream\.py' } |
    Select-Object ProcessId, CommandLine | Format-Table -AutoSize
}